from itertools import product
from quickannotator.constants import PolygonOperations
from quickannotator.db.crud.annotation import AnnotationStore, build_export_filepath
from quickannotator.db.crud.image import get_image_by_id
from quickannotator.db.crud.tile import TileStoreFactory
from quickannotator.db.fsmanager import fsmanager
from .utils import AnnotationExporter, compute_actor_name, GeometryOperation
import quickannotator.db.models as db_models
from . import models as server_models
from quickannotator import constants
from quickannotator.dl.utils import CacheableMask, MaskCacheManager

from flask.views import MethodView
from flask import Response
from shapely.geometry import shape, mapping
import json
import geojson
from typing import List
from flask_smorest import Blueprint
from datetime import datetime
import os
import logging
from quickannotator.db import db_session

bp = Blueprint('annotation', __name__, description='Annotation operations')

# Set up logging
logger = logging.getLogger(constants.LoggerNames.FLASK.value)
mask_cache_manager = MaskCacheManager()

@bp.route('/<int:image_id>/<int:annotation_class_id>')
class Annotation(MethodView):
    @bp.arguments(server_models.GetAnnArgsSchema, location='query')
    @bp.response(200, server_models.AnnRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     returns an Annotation
        """
        in_work_mag = False

        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=in_work_mag, simplify_tolerance=args.get('simplify_tolerance', 0.0))
        result: db_models.Annotation = store.get_annotation_by_id(args['annotation_id'])
        return result, 200

    @bp.arguments(server_models.PostAnnsArgsSchema, location='json')
    @bp.response(200, server_models.AnnRespSchema(many=True))
    @bp.alt_response(400, description="Bad Request: Annotations cannot be saved in tiles that do not intersect the mask.")
    def post(self, args, image_id, annotation_class_id):
        """Post new annotations to the db."""
        is_gt = True
        in_work_mag = False

        polygons: List[geojson.Polygon] = args['polygons']
        store = AnnotationStore(image_id, annotation_class_id, is_gt=is_gt, in_work_mag=in_work_mag)
        anns = store.insert_annotations([shape(poly) for poly in polygons])

        # Check if the annotations are in tiles that intersect the tissue mask
        tilestore = TileStoreFactory.get_tilestore()
        tile_ids_intersecting_mask, _, _ = tilestore.get_tile_ids_intersecting_mask(image_id, annotation_class_id)
        polygon_tile_ids = {ann.tile_id for ann in anns}
        if annotation_class_id != constants.MASK_CLASS_ID:
            non_intersecting_tile_ids = polygon_tile_ids - set(tile_ids_intersecting_mask)
            if non_intersecting_tile_ids:  # If there are any tile IDs that do not intersect the mask
                error_message = f"Annotations cannot be saved in tiles that do not intersect the mask: {non_intersecting_tile_ids}"
                [store.delete_annotations_by_tile(tile_id) for tile_id in non_intersecting_tile_ids]    # db_session.rollback() does not prevent the annotations from being saved, so we delete them manually. TODO: proactively check polygons before saving them.
                logger.error(error_message)
                db_session.rollback()   # NOTE: This currently does not prevent the annotations from being saved.
                return {}, 400
        
        # Invalidate the mask cache for the tiles where annotations were saved

        for tile_id in polygon_tile_ids:
            mask_cache_manager.invalidate(CacheableMask.get_key(image_id, annotation_class_id, tile_id))

        tilestore.upsert_gt_tiles(image_id, annotation_class_id, polygon_tile_ids)

        return anns, 200

    @bp.arguments(server_models.PutAnnArgsSchema, location='json')
    @bp.response(201, server_models.AnnRespSchema)
    def put(self, args, image_id, annotation_class_id):
        """     create or update an annotation directly in the db
        """
        in_work_mag = False

        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=in_work_mag)
        ann = store.update_annotation(args['annotation_id'], shape(args['polygon']))
        # Invalidate the mask cache for the annotation
        if ann is not None:  # Only invalidate if the tile_id is set
            mask_cache_manager.invalidate(CacheableMask.get_key(image_id, annotation_class_id, ann.tile_id))

        return ann, 201
    

    @bp.arguments(server_models.DeleteAnnArgsSchema, location='query')
    def delete(self, args, image_id, annotation_class_id):
        """     delete an annotation
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'])
        annotation = store.get_annotation_by_id(args['annotation_id'])
        result = store.delete_annotation(args['annotation_id'])

        # Invalidate the mask cache for the annotation
        mask_cache_manager.invalidate(CacheableMask.get_key(image_id, annotation_class_id, annotation.tile_id))

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
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=in_work_mag, simplify_tolerance=args.get('simplify_tolerance', 0.0))
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

        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=in_work_mag, simplify_tolerance=args.get('simplify_tolerance', 0.0))
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

        resp = {field: args[field] for field in server_models.AnnRespSchema().fields.keys() if field in args} # Basically a copy of args without "polygon2" or "operation"
        try:
            if operation == PolygonOperations.UNION:
                result = GeometryOperation.union(poly1, poly2)
            elif operation == PolygonOperations.DIFFERENCE:
                result = GeometryOperation.difference(poly1, poly2)
        except ValueError as e:
            logger.error(str(e))
            return {"message": str(e)}, 400
        
        
        # unfortunately we have to lose the dictionary format because we are mimicking the geojson string outputted by the db.
        
        if result is None:
            resp['polygon'] = None
            resp['centroid'] = None
            resp['area'] = 0
            return resp, 200
        resp['polygon'] = json.dumps(mapping(result))
        resp['centroid'] = json.dumps(mapping(result.centroid))   
        resp['area'] = result.area

        return resp, 200
    

@bp.route('/export/server')
class ExportAnnotationsToServer(MethodView):
    @bp.arguments(server_models.ExportToServerSchema, location='query')
    @bp.response(200, server_models.ExportServerRespSchema)
    def post(self, args):
        """ Export annotations for multiple images and annotation classes to the server """

        image_ids = args['image_ids']
        annotation_class_ids = args['annotation_class_ids']
        is_gt = True
        project_id = get_image_by_id(image_ids[0]).project_id     # NOTE: This is only used for naming the actor, so it's not critical.

        # TODO: add support for multiple formats
        export_formats = args['export_formats']

        timestamp = datetime.now()

        filepaths = [
            build_export_filepath(image_id=image_id,
                                  annotation_class_id=annotation_class_id,
                                  is_gt=is_gt,
                                  extension=constants.ExportFormatExtensions.GEOJSON,
                                  relative=True,
                                  timestamp=timestamp)
            for image_id, annotation_class_id in list(product(image_ids, annotation_class_ids))
        ]

        actor_name = compute_actor_name(project_id, constants.NamedRayActorType.ANNOTATION_EXPORTER)
        exporter = AnnotationExporter.options(name=actor_name).remote(image_ids, annotation_class_ids)
        exporter.export_to_server_fs.remote(export_formats, timestamp)

        return {"actor_name": actor_name, "filepaths": filepaths}, 202
    

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
        project_id = get_image_by_id(image_ids[0]).project_id     # NOTE: This is only used for naming the actor, so it's not critical.

        actor_name = compute_actor_name(project_id, constants.NamedRayActorType.ANNOTATION_EXPORTER)
        exporter = AnnotationExporter.options(name=actor_name).remote(image_ids, annotation_class_ids)
        exporter.export_to_dsa.remote(api_uri, api_key, folder_id)

        # Return the progress actor handle so the client can poll for updates
        return {"actor_name": actor_name}, 202
    

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