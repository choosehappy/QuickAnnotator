from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.tile import TileStoreFactory
from .utils import ProgressTracker, AnnotationExporter
from quickannotator.db.crud.annotation import stream_annotations_tar
import quickannotator.db.models as db_models
from . import models as server_models
from quickannotator import constants
from quickannotator.db.crud.annotation import build_annotation_table_name

from flask.views import MethodView
from flask import Response
from shapely.geometry import shape, mapping
import json
import geojson
from typing import List
from flask_smorest import Blueprint
from datetime import datetime
import os
import numpy as np
import time
import ray

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
    
# @bp.route('/download/<int:image_id>/<int:annotation_class_id>/<str:format>')
# class DownloadAnnotations(MethodView):
#     def get(self, image_id, annotation_class_id, format):
#         """   download a tar archive corresponding to a single image and annotation class   """
#         # check if a tar file in the correct format already exists within the directory structure.

@bp.route('/export/local')
class DownloadAnnotations(MethodView):
    @bp.arguments(server_models.DownloadAnnsArgsSchema, location='json')
    def post(self, args):
        """ Export annotations for multiple images and annotation classes as a TAR file with progress updates """

        image_ids = np.array(args['image_ids'])
        annotation_class_ids = np.array(args['annotation_class_ids'])
        annotations_format = args.get('format', 'geojson')

        # Compute the cartesian product of image_ids and annotation_class_ids
        image_ids_grid, annotation_class_ids_grid = np.meshgrid(image_ids, annotation_class_ids, indexing='ij')
        image_class_pairs = list(zip(image_ids_grid.ravel(), annotation_class_ids_grid.ravel()))

        tablenames = [build_annotation_table_name(image_id, annotation_class_id, True) for image_id, annotation_class_id in image_class_pairs]

        # Use a generator-based function to stream the tarfile with progress updates


        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        headers = {
            "Content-Disposition": f"attachment; filename=annotations_{timestamp}.tar",
            "Content-Type": "application/octet-stream",
        }

        # Return a streaming response with progress updates
        return Response(stream_annotations_tar(tablenames), headers=headers, direct_passthrough=True)

@bp.route('/export/server')
class ExportAnnotationsToServer(MethodView):
    @bp.arguments(server_models.DownloadAnnsArgsSchema, location='query')
    def post(self, args):
        """ Export annotations for multiple images and annotation classes to the server """

        image_ids = args['image_ids']
        annotation_class_ids = args['annotation_class_ids']
        format = args.get('format', 'geojson')
        # write_annotations_to_tarfile(image_ids, annotation_class_ids, format)
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
        folder_id = args['folder_id']
        progress_actor = ProgressTracker.remote(len(image_ids) * len(annotation_class_ids))
        exporter = AnnotationExporter.remote(image_ids, annotation_class_ids, progress_actor)
        exporter.process_annotations.remote(api_uri, api_key, folder_id)

        # TODO: remove this once we have a proper progress tracking system
        # while True:
        #     progress = ray.get(progress_actor.get_progress.remote())
        #     print(f"Progress: {progress:.2f}%")
        #     if progress >= 100:
        #         break
        #     time.sleep(1)

        # Return the progress actor handle so the client can poll for updates
        return {"message": "Annotations export initiated", "progress_actor_id": progress_actor._actor_id.hex()}, 202
    