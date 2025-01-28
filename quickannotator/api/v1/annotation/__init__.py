from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import shapely.wkt
from sqlalchemy import Table
from shapely.geometry import shape, mapping
import json
from geojson import Point


from ..utils.shared_crud import compute_custom_metrics
import quickannotator.db as qadb
from .helper import (
    annotations_within_bbox_spatial,
    get_annotations_for_tile
)
from quickannotator.db import create_dynamic_model, build_annotation_table_name, Image, AnnotationClass
from datetime import datetime
from quickannotator.api.v1.tile.helper import upsert_tile, get_tile_id_for_point
from quickannotator.api.v1.image.helper import get_image_by_id
from quickannotator.api.v1.annotation_class.helper import get_annotation_class_by_id

bp = Blueprint('annotation', __name__, description='Annotation operations')


# ------------------------ MODELS ------------------------
class AnnRespSchema(SQLAlchemyAutoSchema):
    """     Annotation response schema      """
    class Meta:
        model = qadb.Annotation
        include_fk = True
        exclude = ("image_id", "isgt")
    centroid = qadb.GeometryField()
    polygon = qadb.GeometryField()
    datetime = fields.DateTime(format='iso')

class GetAnnArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    annotation_id = fields.Int(required=True)

class GetAnnSearchArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    x1 = fields.Int(required=False)
    y1 = fields.Int(required=False)
    x2 = fields.Int(required=False)
    y2 = fields.Int(required=False)
    polygon = qadb.GeometryField(required=False)

class GetAnnByTileArgsSchema(Schema):
    is_gt = fields.Bool(required=True)

class PostAnnArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    polygon = qadb.GeometryField(required=True)

class OperationArgsSchema(AnnRespSchema):
    operation = fields.Integer(required=True)  # Default 0 for union.
    polygon2 = qadb.GeometryField(required=True)    # The second polygon

class PutAnnArgsSchema(AnnRespSchema):
    is_gt = fields.Bool(required=True)

class DeleteAnnArgsSchema(GetAnnArgsSchema):
    pass

class PostDryRunArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    polygon = fields.String(required=True)
    script = fields.Str(required=True)

# ------------------------ ROUTES ------------------------

@bp.route('/<int:image_id>/<int:annotation_class_id>')
class Annotation(MethodView):
    @bp.arguments(GetAnnArgsSchema, location='query')
    @bp.response(200, AnnRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     returns an Annotation
        """
        model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, args['is_gt']))
        result = qadb.db.session.query(model).filter_by(id=args['annotation_id']).first()
        return result, 200

    @bp.arguments(PostAnnArgsSchema, location='json')
    @bp.response(200, AnnRespSchema)
    def post(self, args, image_id, annotation_class_id):
        """     post a new annotation to the db. 
        
        This method is primarily used for ground truth annotations. Predictions should only by saved by the model.
        """
        poly: shapely.geometry.base.BaseGeometry = shape(args['polygon'])
        
        # Get the tile id.
        # NOTE: The client is aware of the tilesize and image dimensions. Consider passing this information in the request or even calculating the tile_id client-side.
        image: Image = get_image_by_id(image_id)
        annotation_class: AnnotationClass = get_annotation_class_by_id(annotation_class_id)
        tile_id = get_tile_id_for_point(annotation_class.tilesize, poly.centroid.x, poly.centroid.y, image.width, image.height)
        
        model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, args['is_gt']))
        ann = model(
            image_id=None,
            annotation_class_id=None,
            isgt=None,
            centroid=poly.centroid.wkt,
            area=poly.area,
            polygon=poly.wkt,
            custom_metrics=compute_custom_metrics(),
            tile_id=tile_id,
            datetime=datetime.now()
        )

        qadb.db.session.add(ann)
        qadb.db.session.commit()
        
        if args['is_gt']:   # Not seen by the deep learning model
            upsert_tile(annotation_class_id, image_id, tile_id, hasgt=True)
        
        return ann, 200

    @bp.arguments(PutAnnArgsSchema, location='json')
    @bp.response(201, AnnRespSchema)
    def put(self, args, image_id, annotation_class_id):
        """     create or update an annotation directly in the db
        """
        model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, args['is_gt']))

        ann: Annotation = qadb.db.session.query(model).filter_by(id=args['id']).first()
        
        if ann: # Update the existing annotation
            ann.centroid = shape(args['centroid']).wkt
            ann.area = args['area']
            ann.polygon = shape(args['polygon']).wkt
            ann.custom_metrics = args['custom_metrics']
            ann.tile_id = args['tile_id']
            ann.datetime = datetime.now()
        else: # Create a new annotation
            new_ann = model(
                image_id=None,
                annotation_class_id=None,
                isgt=None,
                centroid=args['centroid'],
                area=args['area'],
                polygon=args['polygon'],
                custom_metrics=args['custom_metrics'],
                tile_id=args['tile_id'],
                datetime=datetime.now()
            )
            qadb.db.session.add(new_ann)
        qadb.db.session.commit()
        
        if args['is_gt']:
            upsert_tile(annotation_class_id, image_id, args['tile_id'], hasgt=True)

        return ann, 201

    @bp.arguments(DeleteAnnArgsSchema, location='query')
    def delete(self, args, image_id, annotation_class_id):
        """     delete an annotation
        """
        model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, args['is_gt']))
        result = qadb.db.session.query(model).filter_by(id=args['annotation_id']).delete()

        if result:
            qadb.db.session.commit()
            return {}, 204
        else:
            return {"message": "Annotation not found"}, 404

#################################################################################
@bp.route('/<int:image_id>/<int:annotation_class_id>/search')
class SearchAnnotations(MethodView):
    @bp.arguments(GetAnnSearchArgsSchema, location='query')
    @bp.response(200, AnnRespSchema(many=True))
    def get(self, args, image_id, annotation_class_id):
        """Search for annotations

        # Implementation
        - Will need to determine the return type. Should it be pure geojson?
        """
        table_name = build_annotation_table_name(image_id, annotation_class_id, args['is_gt'])
        table = Table(table_name, qadb.db.metadata, autoload_with=qadb.db.engine)

        if "polygon" in args:
            # search for annotations within the bounding box
            pass
        elif "x1" in args and "y1" in args and "x2" in args and "y2" in args:
            # return all annotations
            return annotations_within_bbox_spatial(table_name, args['x1'], args['y1'], args['x2'], args['y2']), 200
        else:
            stmt = table.select()
            result = qadb.db.session.execute(stmt).fetchall()
            return result, 200
        
@bp.route('/<int:image_id>/<int:annotation_class_id>/<int:tile_id>')
class AnnotationByTile(MethodView):
    @bp.arguments(GetAnnByTileArgsSchema, location='query')
    @bp.response(200, AnnRespSchema(many=True))
    def get(self, args, image_id, annotation_class_id, tile_id):
        """     get all annotations for a given tile
        """
        result = get_annotations_for_tile(image_id, annotation_class_id, tile_id, args['is_gt'])
        return result, 200
        
@bp.route('/<int:annotation_class_id>/dryrun')
class AnnotationDryRun(MethodView):
    @bp.arguments(PostDryRunArgsSchema, location='json')
    def post(self, args, annotation_class_id):
        """     perform a dry run for the given annotation

        """

        return 200

@bp.route('/operation')
class AnnotationOperation(MethodView):
    @bp.arguments(OperationArgsSchema, location='json')
    @bp.response(200, AnnRespSchema)
    def post(self, args):
        """     perform a union of two annotations

        """

        poly1 = shape(args['polygon'])
        poly2 = shape(args['polygon2'])
        operation = args['operation']

        if operation == 0:
            union = poly1.union(poly2)
        
            resp = {field: args[field] for field in AnnRespSchema.Meta.model.__table__.columns.keys() if field in args} # Basically a copy of args without "polygon2" or "operation"
            # unfortunately we have to lose the dictionary format because we are mimicking the geojson string outputted by the db.
            resp['polygon'] = json.dumps(mapping(union))
            resp['centroid'] = json.dumps(mapping(union.centroid))   
            resp['area'] = union.area

        return resp, 200