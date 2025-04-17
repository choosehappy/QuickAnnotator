from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.tile import TileStoreFactory
from quickannotator.db.crud.annotation import write_annotations_to_tarfile
import quickannotator.db.models as db_models
from . import models as server_models

from flask.views import MethodView
from flask import Response
from shapely.geometry import shape, mapping
import json
import geojson
from typing import List
from flask_smorest import Blueprint
from datetime import datetime

bp = Blueprint('annotation', __name__, description='Annotation operations')


@bp.route('/<int:image_id>/<int:annotation_class_id>')
class Annotation(MethodView):
    @bp.arguments(server_models.GetAnnArgsSchema, location='query')
    @bp.response(200, server_models.AnnRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     returns an Annotation
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        result: db_models.Annotation = store.get_annotation_by_id(args['annotation_id'])
        return result, 200

    @bp.arguments(server_models.PostAnnsArgsSchema, location='json')
    @bp.response(200, server_models.AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     post new annotations to the db. 
        
        This method is primarily used for ground truth annotations. Predictions should only by saved by the model.
        """
        polygons: List[geojson.Polygon] = args['polygons']
        store = AnnotationStore(image_id, annotation_class_id, is_gt=True, in_work_mag=False)
        anns = store.insert_annotations([shape(poly) for poly in polygons])
        tilestore = TileStoreFactory.get_tilestore()
        tilestore.upsert_gt_tiles(image_id, annotation_class_id, {ann.tile_id for ann in anns})

        return anns, 200

    @bp.arguments(server_models.PutAnnArgsSchema, location='json')
    @bp.response(201, server_models.AnnRespSchema)
    def put(self, args, image_id, annotation_class_id):
        """     create or update an annotation directly in the db
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        ann = store.update_annotation(args['annotation_id'], shape(args['polygon']))

        return ann, 201
    @bp.arguments(server_models.DeleteAnnArgsSchema, location='query')
    def delete(self, args, image_id, annotation_class_id):
        """     delete an annotation
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'])
        result = store.delete_annotation(args['annotation_id'])

        if result:
            return {}, 204
        else:
            return {"message": "Annotation not found"}, 404


@bp.route('/<int:image_id>/<int:annotation_class_id>/tileids')
class AnnotationByTileIds(MethodView):
    @bp.arguments(server_models.GetAnnByTileIdsArgsSchema, location='json')
    @bp.response(200, server_models.AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     get all annotations for a given tile
        """

        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        anns = store.get_annotations_for_tiles(args['tile_ids'])

        return anns, 200
    
@bp.route('/<int:image_id>/<int:annotation_class_id>/withinpoly')
class AnnotationsWithinPolygon(MethodView):
    @bp.arguments(server_models.GetAnnWithinPolyArgsSchema, location='json')
    @bp.response(200, server_models.AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     get all annotations within a polygon
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        anns = store.get_annotations_within_poly(shape(args['polygon']))
        return anns, 200

# TODO: This endpoint will be needed when we build in custom scripting.
# @bp.route('/<int:annotation_class_id>/dryrun')
# class AnnotationDryRun(MethodView):
#     @bp.arguments(PostDryRunArgsSchema, location='json')
#     def post(self, args, annotation_class_id):
#         """     perform a dry run for the given annotation

#         """

#         return 200

@bp.route('/operation')
class AnnotationOperation(MethodView):
    @bp.arguments(server_models.OperationArgsSchema, location='json')
    @bp.response(200, server_models.AnnRespSchema)
    def post(self, args):
        """     perform a union of two annotations

        """

        poly1 = shape(args['polygon'])
        poly2 = shape(args['polygon2'])
        operation = args['operation']

        if operation == 0:
            union = poly1.union(poly2)
        
            resp = {field: args[field] for field in server_models.AnnRespSchema().fields.keys() if field in args} # Basically a copy of args without "polygon2" or "operation"
            # unfortunately we have to lose the dictionary format because we are mimicking the geojson string outputted by the db.
            resp['polygon'] = json.dumps(mapping(union))
            resp['centroid'] = json.dumps(mapping(union.centroid))   
            resp['area'] = union.area

        return resp, 200
    

@bp.route('/export/local')
class DownloadAnnotations(MethodView):
    @bp.arguments(server_models.DownloadAnnsArgsSchema, location='json')
    @bp.response(200, {"format": "binary", "type": "string"}, content_type="application/x-tar")
    def post(self, args):
        """ Export annotations for multiple images and annotation classes as a TAR file """

        image_ids = args['image_ids']
        annotation_class_ids = args['annotation_class_ids']
        format = args.get('format', 'geojson')
        tar_buffer = write_annotations_to_tarfile(image_ids, annotation_class_ids, format)
        response = Response(tar_buffer.getvalue(), mimetype="application/x-tar")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response.headers.set("Content-Disposition", "attachment", filename=f"annotations_{timestamp}.tar.gz")
        return response

@bp.route('/export/server')
class ExportAnnotationsToServer(MethodView):
    @bp.arguments(server_models.DownloadAnnsArgsSchema, location='query')
    def post(self, args):
        """ Export annotations for multiple images and annotation classes to the server """

        image_ids = args['image_ids']
        annotation_class_ids = args['annotation_class_ids']
        format = args.get('format', 'geojson')
        write_annotations_to_tarfile(image_ids, annotation_class_ids, format)
        return {"message": "Annotations exported successfully"}, 200
    

@bp.route('/export/dsa')
class ExportAnnotationsToDSA(MethodView):
    @bp.arguments(server_models.ExportToDSASchema, location='json')
    def post(self, args):
        """ Export annotations for multiple images and annotation classes to the DSA """

        image_ids = args['image_ids']
        annotation_class_ids = args['annotation_class_ids']
        api_uri = args['api_uri']
        api_key = args['api_key']
        collection_name = args['collection_name']
        folder_name = args['folder_name']

        # Implement the logic to export annotations to DSA here
        # For example, you might want to call a function that handles the export process

        return {"message": "Annotations exported to DSA successfully"}, 200