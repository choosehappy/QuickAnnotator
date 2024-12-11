from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import shapely.wkt
from sqlalchemy import Table
from shapely.geometry import shape, mapping
import json

import quickannotator.db as qadb
from .helper import (
    annotations_within_bbox,
    annotations_within_bbox_spatial,
    retrieve_annotation_table,
    compute_custom_metrics,
    annotation_by_id,
    dynamically_create_model_for_table
)
from datetime import datetime

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
        table = retrieve_annotation_table(image_id, annotation_class_id, args['is_gt'])

        # stmt = table.select().where(table.c.id == args['annotation_id']).with_only_columns(
        #     *(col for col in table.c if col.name != "polygon" and col.name != "centroid"),
        #     table.c.centroid.ST_AsGeoJSON().label('centroid'),
        #     table.c.polygon.ST_AsGeoJSON().label('polygon')
        # )
        # result = qadb.db.session.execute(stmt).first()

        result = annotation_by_id(table, args['annotation_id'])
        return result, 200

    @bp.arguments(PostAnnArgsSchema, location='json')
    @bp.response(200, AnnRespSchema)
    def post(self, args, image_id, annotation_class_id):
        """     process a new annotation

        """

        poly: shapely.geometry.base.BaseGeometry = shape(args['polygon'])

        table = retrieve_annotation_table(image_id, annotation_class_id, args['is_gt'])
        model = dynamically_create_model_for_table(table)

        ann = model(
            image_id=image_id,
            annotation_class_id=annotation_class_id,
            isgt=args['is_gt'],
            centroid=poly.centroid.wkt,
            area=poly.area,
            polygon=poly.wkt,
            custom_metrics=compute_custom_metrics(),
        )

        qadb.db.session.add(ann)
        qadb.db.session.commit()
        # unfortunately the ORM doesn't return the centroid and polygon as geojson. Consider updating the GeometryField to automatically convert EWKB to geojson.
        result = annotation_by_id(table, ann.id)
        return result, 200
    


    @bp.arguments(PutAnnArgsSchema, location='json')
    @bp.response(201, AnnRespSchema)
    def put(self, args, image_id, annotation_class_id):
        """     create or update an annotation directly in the db

        """
        table = retrieve_annotation_table(image_id, annotation_class_id, args['is_gt'])
        model = dynamically_create_model_for_table(table)

        ann = qadb.db.session.query(model).filter_by(id=args['id']).first()
        if ann:
            ann.centroid = shape(args['centroid']).wkt
            ann.area = args['area']
            ann.polygon = shape(args['polygon']).wkt
            ann.custom_metrics = args['custom_metrics']
            ann.datetime = datetime.now()
        else:
            ann = model(
                id=args['id'],
                image_id=image_id,
                annotation_class_id=annotation_class_id,
                isgt=args['is_gt'],
                centroid=args['centroid'],
                area=args['area'],
                polygon=args['polygon'],
                custom_metrics=args['custom_metrics'],
                datetime=datetime.now()
            )
            qadb.db.session.add(ann)
        qadb.db.session.commit()

        result = annotation_by_id(table, ann.id)
        return result, 201

    @bp.arguments(DeleteAnnArgsSchema, location='query')
    def delete(self, args, image_id, annotation_class_id):
        """     delete an annotation

        """
        table = retrieve_annotation_table(image_id, annotation_class_id, args['is_gt'])

        stmt = table.delete().where(table.c.id == args['annotation_id'])
        qadb.db.session.execute(stmt)
        qadb.db.session.commit()
        return {}, 204

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
        gtpred = 'gt' if args['is_gt'] else 'pred'
        table_name = f"{image_id}_{annotation_class_id}_{gtpred}_annotation"
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
        

#################################################################################
# @bp.route('/<int:image_id>/<int:annotation_class_id>/predict')
# class PredictAnnotations(MethodView):
#     """     request new DL model predictions
#     """
#     @bp.arguments(PostAnnArgsSchema, location='json')
#     @bp.response(200, AnnRespSchema(many=True))
#     def post(self, args, image_id, annotation_class_id):

#         return 200

#################################################################################
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