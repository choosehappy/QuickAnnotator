from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from shapely.geometry import shape, mapping
import json
from shapely.affinity import scale
import shapely
from typing import List
import quickannotator.db.models as models
from ..utils.shared_crud import AnnotationStore
import geojson
from quickannotator.api.v1.tile.helper import get_tile
from quickannotator.constants import TileStatus
from datetime import datetime
from quickannotator.api.v1.utils.shared_crud import upsert_tiles


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

class GetAnnByTileIdsArgsSchema(Schema):
    tile_ids = fields.List(fields.Int(), required=True)
    is_gt = fields.Bool(required=True)

class PostAnnsArgsSchema(Schema):
    polygons = fields.List(models.GeometryField(), required=True)

class OperationArgsSchema(AnnRespSchema):
    operation = fields.Integer(required=True)  # Default 0 for union.
    polygon2 = models.GeometryField(required=True)    # The second polygon

class PutAnnArgsSchema(Schema):
    annotation_id = fields.Int(required=True)
    polygon = models.GeometryField(required=True)
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
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        result: models.Annotation = store.get_annotation_by_id(args['annotation_id'])
        return result, 200

    @bp.arguments(PostAnnsArgsSchema, location='json')
    @bp.response(200, AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     post new annotations to the db. 
        
        This method is primarily used for ground truth annotations. Predictions should only by saved by the model.
        """
        polygons: List[geojson.Polygon] = args['polygons']
        store = AnnotationStore(image_id, annotation_class_id, is_gt=True, in_work_mag=False)
        anns = store.insert_annotations([shape(poly) for poly in polygons])

        return anns, 200

    @bp.arguments(PutAnnArgsSchema, location='json')
    @bp.response(201, AnnRespSchema)
    def put(self, args, image_id, annotation_class_id):
        """     create or update an annotation directly in the db
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        ann = store.update_annotation(args['annotation_id'], shape(args['polygon']))

        return ann, 201
    @bp.arguments(DeleteAnnArgsSchema, location='query')
    def delete(self, args, image_id, annotation_class_id):
        """     delete an annotation
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'])
        result = store.delete_annotation(args['annotation_id'])

        if result:
            return {}, 204
        else:
            return {"message": "Annotation not found"}, 404

################################################################################
# # DEPRECATED
# @bp.route('/<int:image_id>/<int:annotation_class_id>/search')
# class SearchAnnotations(MethodView):
#     @bp.arguments(GetAnnSearchArgsSchema, location='query')
#     @bp.response(200, AnnRespSchema(many=True))
#     def get(self, args, image_id, annotation_class_id):
#         """Search for annotations

#         # Implementation
#         - Will need to determine the return type. Should it be pure geojson?
#         """
#         table_name = build_annotation_table_name(image_id, annotation_class_id, args['is_gt'])
#         table = Table(table_name, db_session.bind.metadata, autoload_with=db_session.bind)

#         if "polygon" in args:
#             # search for annotations within the bounding box
#             pass
#         elif "x1" in args and "y1" in args and "x2" in args and "y2" in args:
#             # return all annotations
#             return annotations_within_bbox_spatial(table_name, args['x1'], args['y1'], args['x2'], args['y2']), 200
#         else:
#             stmt = table.select()
#             result = db_session.execute(stmt).fetchall()
#             return result, 200
        

@bp.route('/<int:image_id>/<int:annotation_class_id>/tileids')
class AnnotationByTileIds(MethodView):
    @bp.arguments(GetAnnByTileIdsArgsSchema, location='json')
    @bp.response(200, AnnRespSchema(many=True))
    def get(self, args, image_id, annotation_class_id):
        """     get all annotations for a given tile
        """

        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        anns = store.get_annotations_for_tiles(args['tile_ids'])

        return anns, 200

        # else:
        #     store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        #     anns = store.get_predictions_for_tiles(args['tile_ids'])

        # if args['is_gt']:
        #     store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        #     anns = store.get_annotations_for_tiles([tile_id])
        # else:
        #     tile = get_tile(image_id=image_id, annotation_class_id=annotation_class_id, tile_id=tile_id)
        #     if not tile or tile.pred_status == TileStatus.UNSEEN:
        #         upsert_tiles(image_id=image_id, annotation_class_id=annotation_class_id, tile_ids=[tile_id], pred_status=TileStatus.STARTPROCESSING)
        #         return {"message": "No predictions for this tile"}, 404
        #     elif tile.pred_status == TileStatus.STARTPROCESSING:
        #         pass
        #     elif tile.pred_status == TileStatus.PROCESSING:
        #         pass
        #     elif tile.pred_status == TileStatus.DONEPROCESSING:
        #         # If the client wants prediction to be refreshed
        #         tile.pred_status = TileStatus.STARTPROCESSING
        #         tile.pred_datetime = datetime.now()
                
        #     # Lastly, get all predictions currently associated with the tile
        #     store = AnnotationStore(image_id, annotation_class_id, is_gt=False, in_work_mag=False)
        #     anns = store.get_predictions_for_tiles([tile_id])
        # return anns, 200
    
# We need a separate method for getting predictions because here we have a different response type. We want to render a gray box wherever there are pending predictions.
@bp.route('/<int:image_id>/<int:annotation_class_id>/predictions')
    
@bp.route('/<int:image_id>/<int:annotation_class_id>/withinpoly')
class AnnotationsWithinPolygon(MethodView):
    @bp.arguments(GetAnnWithinPolyArgsSchema, location='json')
    @bp.response(200, AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     get all annotations within a polygon
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        anns = store.get_annotations_within_poly(shape(args['polygon']))
        return anns, 200

# DEPRECATED      
# @bp.route('/<int:annotation_class_id>/dryrun')
# class AnnotationDryRun(MethodView):
#     @bp.arguments(PostDryRunArgsSchema, location='json')
#     def post(self, args, annotation_class_id):
#         """     perform a dry run for the given annotation

#         """

#         return 200

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