from itertools import product
from quickannotator.constants import PolygonOperations
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.image import get_image_by_id
from quickannotator.db.crud.tile import TileStoreFactory
from quickannotator.db.utils import build_tarpath
from quickannotator.db.fsmanager import fsmanager
from .utils import ProgressTracker, AnnotationExporter
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
        in_work_mag = False

        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=in_work_mag)
        result: db_models.Annotation = store.get_annotation_by_id(args['annotation_id'])
        return result, 200

    @bp.arguments(server_models.PostAnnsArgsSchema, location='json')
    @bp.response(200, server_models.AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     post new annotations to the db. 
        
        This method is primarily used for ground truth annotations. Predictions should only by saved by the model.
        """
        is_gt = True
        in_work_mag = False

        polygons: List[geojson.Polygon] = args['polygons']
        store = AnnotationStore(image_id, annotation_class_id, is_gt=is_gt, in_work_mag=in_work_mag)
        anns = store.insert_annotations([shape(poly) for poly in polygons])
        tilestore = TileStoreFactory.get_tilestore()
        tilestore.upsert_gt_tiles(image_id, annotation_class_id, {ann.tile_id for ann in anns})

        return anns, 200

    @bp.arguments(server_models.PutAnnArgsSchema, location='json')
    @bp.response(201, server_models.AnnRespSchema)
    def put(self, args, image_id, annotation_class_id):
        """     create or update an annotation directly in the db
        """
        in_work_mag = False

        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=in_work_mag)
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
        in_work_mag = False

        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=in_work_mag)
        anns = store.get_annotations_for_tiles(args['tile_ids'])

        return anns, 200
    
@bp.route('/<int:image_id>/<int:annotation_class_id>/withinpoly')
class AnnotationsWithinPolygon(MethodView):
    @bp.arguments(server_models.GetAnnWithinPolyArgsSchema, location='json')
    @bp.response(200, server_models.AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     get all annotations within a polygon
        """
        in_work_mag = False

        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=in_work_mag)
        anns = store.get_annotations_within_poly(shape(args['polygon']))
        return anns, 200


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

        if operation == PolygonOperations.UNION:
            union = poly1.union(poly2)
        
            resp = {field: args[field] for field in server_models.AnnRespSchema().fields.keys() if field in args} # Basically a copy of args without "polygon2" or "operation"
            # unfortunately we have to lose the dictionary format because we are mimicking the geojson string outputted by the db.
            resp['polygon'] = json.dumps(mapping(union))
            resp['centroid'] = json.dumps(mapping(union.centroid))   
            resp['area'] = union.area

        return resp, 200
    

@bp.route('/export/server')
class ExportAnnotationsToServer(MethodView):
    @bp.arguments(server_models.ExportToServerSchema, location='query')
    @bp.response(200, server_models.ExportServerRespSchema(many=True))
    def post(self, args):
        """ Export annotations for multiple images and annotation classes to the server """

        image_ids = args['image_ids']
        annotation_class_ids = args['annotation_class_ids']
        is_gt = True

        # TODO: add support for multiple formats
        annotations_format = args['annotations_format']
        props_format = args['props_format']

        resp = [{
            "filepath": fsmanager.nas_write.global_to_relative(build_tarpath(image_id, annotation_class_id, is_gt)),
            } for image_id, annotation_class_id in list(product(image_ids, annotation_class_ids))]

        exporter = AnnotationExporter.remote(image_ids, annotation_class_ids)
        exporter.export_remotely.remote()

        return resp, 200
    

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
        exporter = AnnotationExporter.remote(image_ids, annotation_class_ids)
        exporter.export_to_dsa.remote(api_uri, api_key, folder_id)

        # Return the progress actor handle so the client can poll for updates
        return {"message": "Annotations export initiated", "progress_actor_id": exporter._actor_id.hex()}, 202
    

@bp.route('/export/download/<path:tarpath>')
class DownloadAnnotations(MethodView):
    def get(self, tarpath):
        """ Download existing annotations by passing in image_id, annotation_class_id, and tarname """

        fullpath = fsmanager.nas_write.relative_to_global(tarpath)

        if not os.path.exists(fullpath):
            return {"message": "Tar file not found"}, 404

        headers = {
            "Content-Disposition": f"attachment; filename={os.path.basename(tarpath)}",
            "Content-Type": "application/octet-stream",
        }

        def generate():
            with open(fullpath, 'rb') as f:
                while chunk := f.read(constants.STREAMING_CHUNK_SIZE):
                    yield chunk

        return Response(generate(), headers=headers, direct_passthrough=True)