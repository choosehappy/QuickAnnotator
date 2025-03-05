from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from sqlalchemy import Table
from shapely.geometry import shape, mapping
import json
from geojson import Polygon
from shapely.affinity import scale
import shapely
from shapely.strtree import STRtree

from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor
import quickannotator.db.models as models
from quickannotator.db import db_session
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from .helper import (
    annotations_within_bbox_spatial,
    get_annotations_for_tile,
    get_annotations_for_tiles,
    get_annotation_by_id
)
from datetime import datetime
from quickannotator.api.v1.tile.helper import upsert_tile, tile_intersects_mask, get_tile_ids_intersecting_mask, get_tile_ids_intersecting_polygons
from quickannotator.api.v1.image.utils import get_image_by_id
from quickannotator.api.v1.annotation_class.helper import get_annotation_class_by_id
from quickannotator.api.v1.utils.shared_crud import insert_new_annotation, get_annotation_query
from quickannotator.api.v1.utils.coordinate_space import get_tilespace
import quickannotator.constants as constants


bp = Blueprint('annotation', __name__, description='Annotation operations')


# ------------------------ MODELS ------------------------
class AnnRespSchema(Schema):
    """     Annotation response schema      """
    id = fields.Int()
    tile_id = fields.Int()
    centroid = models.GeometryField()
    polygon = models.GeometryField()
    area = fields.Float()
    custom_metrics = fields.Dict()

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
    polygon = models.GeometryField(required=False)

class GetAnnWithinPolyArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    polygon = models.GeometryField(required=True)

class GetAnnByTileArgsSchema(Schema):
    is_gt = fields.Bool(required=True)

class PostAnnArgsSchema(Schema):
    polygon = models.GeometryField(required=True)

class OperationArgsSchema(AnnRespSchema):
    operation = fields.Integer(required=True)  # Default 0 for union.
    polygon2 = models.GeometryField(required=True)    # The second polygon

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
        scale_factor = base_to_work_scaling_factor(image_id, annotation_class_id)
        model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, args['is_gt']))
        result = get_annotation_query(model, 1/scale_factor).filter_by(id=args['annotation_id']).first()
        return result, 200

    @bp.arguments(PostAnnArgsSchema, location='json')
    @bp.response(200, AnnRespSchema)
    def post(self, args, image_id, annotation_class_id):
        """     post a new annotation to the db. 
        
        This method is primarily used for ground truth annotations. Predictions should only by saved by the model.
        """
        # scale the polygon to the working magnification
        scale_factor = base_to_work_scaling_factor(image_id, annotation_class_id)
        poly = scale(geom=shape(args['polygon']), xfact=scale_factor, yfact=scale_factor, origin=(0, 0))
        
        
        # Get the tile id.
        tilespace = get_tilespace(image_id, annotation_class_id, in_work_mag=True)  # Polygon is already scaled to the working magnification
        tile_id = tilespace.point_to_tileid(poly.centroid.x, poly.centroid.y)
        
        ann = insert_new_annotation(image_id, annotation_class_id, True, tile_id, poly)
        
        if tile_intersects_mask(image_id, annotation_class_id, tile_id):
            upsert_tile(annotation_class_id, image_id, tile_id, hasgt=True)
        else:
            return {"message": "Tile does not intersect with the tissue mask and will not be inserted."}, 400

        ann = get_annotation_query(ann.__class__).filter_by(id=ann.id).first()
        
        return ann, 200

    @bp.arguments(PutAnnArgsSchema, location='json')
    @bp.response(201, AnnRespSchema)
    def put(self, args, image_id, annotation_class_id):
        """     create or update an annotation directly in the db
        """
        model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, args['is_gt']))

        scale_factor = base_to_work_scaling_factor(image_id, annotation_class_id)
        poly = scale(geom=shape(args['polygon']), xfact=scale_factor, yfact=scale_factor, origin=(0, 0))
        centroid = scale(geom=shape(args['centroid']), xfact=scale_factor, yfact=scale_factor, origin=(0, 0))

        # We get the full ORM object here so that we can set values.
        ann: Annotation = db_session.query(model).filter_by(id=args['id']).first()
        if ann: # Update the existing annotation
            ann.centroid = centroid.wkt
            ann.area = args['area']
            ann.polygon = poly.wkt
            ann.custom_metrics = args['custom_metrics']
            ann.tile_id = args['tile_id']
            ann.datetime = datetime.now()
            db_session.commit()
            result = get_annotation_query(model).filter_by(id=ann.id).first()
            return result, 201

        else: # Create a new annotation
            return {"message": "Annotation not found"}, 404

    @bp.arguments(DeleteAnnArgsSchema, location='query')
    def delete(self, args, image_id, annotation_class_id):
        """     delete an annotation
        """
        model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, args['is_gt']))
        result = db_session.query(model).filter_by(id=args['annotation_id']).delete()

        if result:
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
        table = Table(table_name, db_session.bind.metadata, autoload_with=db_session.bind)

        if "polygon" in args:
            # search for annotations within the bounding box
            pass
        elif "x1" in args and "y1" in args and "x2" in args and "y2" in args:
            # return all annotations
            return annotations_within_bbox_spatial(table_name, args['x1'], args['y1'], args['x2'], args['y2']), 200
        else:
            stmt = table.select()
            result = db_session.execute(stmt).fetchall()
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
    
@bp.route('/<int:image_id>/<int:annotation_class_id>/withinpoly')
class AnnotationsWithinPolygon(MethodView):
    @bp.arguments(GetAnnWithinPolyArgsSchema, location='json')
    @bp.response(200, AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     get all annotations within a polygon
        """

        # 1. Get all tiles intersecting the polygon
        tiles_ids_within_mask, _, _ = get_tile_ids_intersecting_mask(image_id, annotation_class_id, constants.MASK_DILATION)

        # NOTE: This method tends to produce false positives due to the mask dilation. Consider interpolating the polygon and setting MASK_DILATION to 0.
        tile_ids_intersecting_polygons, _, _ = get_tile_ids_intersecting_polygons(image_id, annotation_class_id, [args['polygon']], constants.MASK_DILATION)
        tile_ids = set(tile_ids_intersecting_polygons) & set(tiles_ids_within_mask)

        annotations = get_annotations_for_tiles(image_id, annotation_class_id, tile_ids, args['is_gt'])

        # Create a spatial index for the annotations
        # TODO: Consider using the database spatial index for this task.
        polygons = [shapely.from_geojson(ann.polygon) for ann in annotations]
        spatial_index = STRtree(polygons)

        # Query the spatial index for annotations intersecting the polygon
        query_polygon = shape(args['polygon'])
        ids_intersecting_query_poly = spatial_index.query(query_polygon)  # List of polygon indices that intersect the query polygon

        # Filter annotations that intersect the polygon
        filtered_anns = [annotations[i] for i in ids_intersecting_query_poly]
        
        return filtered_anns, 200
        
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
        
            resp = {field: args[field] for field in AnnRespSchema().fields.keys() if field in args} # Basically a copy of args without "polygon2" or "operation"
            # unfortunately we have to lose the dictionary format because we are mimicking the geojson string outputted by the db.
            resp['polygon'] = json.dumps(mapping(union))
            resp['centroid'] = json.dumps(mapping(union.centroid))   
            resp['area'] = union.area

        return resp, 200