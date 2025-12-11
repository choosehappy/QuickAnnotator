from flask.views import MethodView
from quickannotator.db import db_session
from quickannotator.db.crud.tile import TileStoreFactory, TileStore
from quickannotator.constants import TileStatus, MASK_CLASS_ID
import quickannotator.db.models as db_models
from . import models as server_models
from quickannotator.api.v1.utils.coordinate_space import get_tilespace
from flask_smorest import Blueprint
import numpy as np

bp = Blueprint('tile', __name__, description="Tile operations")

@bp.route('/<int:image_id>/<int:annotation_class_id>')
class Tile(MethodView):
    @bp.arguments(server_models.GetTileArgsSchema, location='query')
    @bp.response(200, server_models.TileRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     returns a Tile
        """
        tilestore = TileStoreFactory.get_tilestore()
        result = tilestore.get_tile(image_id, annotation_class_id, args['tile_id'])
        return result, 200

    @bp.arguments(server_models.GetTileArgsSchema, location='query')
    def delete(self, args, image_id, annotation_class_id):
        """     delete a Tile
        """
        db_session.query(db_models.Tile).filter_by(
            image_id=image_id,
            annotation_class_id=annotation_class_id,
            tile_id=args['tile_id']
        ).delete()
        return {}, 204

@bp.route('/<int:image_id>/<int:annotation_class_id>/predict')
class PredictTile(MethodView):
    @bp.arguments(server_models.PostTileArgsSchema, location='query')
    @bp.response(200, server_models.TileRespSchema, description="Staged tile for DL processing")
    def post(self, args, image_id, annotation_class_id):
        """     stage a tile for DL processing     """
        tilestore: TileStore = TileStoreFactory.get_tilestore()
        result = tilestore.upsert_pred_tiles(
            image_id=image_id,
            annotation_class_id=annotation_class_id,
            tile_ids=[args['tile_id']],
            pred_status=TileStatus.STARTPROCESSING,
            process_owns_tile=False
        )

        if len(result) > 0:
            return result[0], 200
        else:
            return {"message": "Failed to stage tile for processing"}, 400

@bp.route('/<int:image_id>/<int:annotation_class_id>/bbox')
class TileBoundingBox(MethodView):
    @bp.arguments(server_models.GetTileArgsSchema, location='query')
    @bp.response(200, server_models.TileBoundingBoxRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     get the bounding box for a given tile as a GeoJSON polygon
        """
        # TODO: support downsample level arg
        tilespace = get_tilespace(image_id=image_id, annotation_class_id=annotation_class_id, in_work_mag=False)
        bbox = tilespace.get_bbox_for_tile(args['tile_id'])
        geojson_polygon = {
            "type": "Polygon",
            "coordinates": [[
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
                [bbox[0], bbox[1]]
            ]]
        }
        return {'bbox_polygon': geojson_polygon}, 200

@bp.route('/<int:image_id>/<int:annotation_class_id>/search/bbox')
class TileIdSearchByBbox(MethodView):
    @bp.arguments(server_models.SearchTileArgsSchema, location='query')
    @bp.response(200, server_models.TileRefRespSchema(many=True))
    def get(self, args, image_id, annotation_class_id):
        """     get all Tiles within a bounding box
        """
        downsample_level = args.get('downsample_level', 0)
        tilespace = get_tilespace(image_id=image_id, annotation_class_id=annotation_class_id, in_work_mag=False)
        downsampled_tilespace = tilespace.get_resampled_tilespace(downsample_level)
        tilestore = TileStoreFactory.get_tilestore()
        
        downsampled_tile_ids_in_bbox = downsampled_tilespace.get_tile_ids_within_bbox((args['x1'], args['y1'], args['x2'], args['y2']))
        tile_ids_in_bbox = np.concatenate([downsampled_tilespace.upsample_tile_id(tile_id, downsample_level) for tile_id in downsampled_tile_ids_in_bbox]).tolist()

        if annotation_class_id != MASK_CLASS_ID:
            tile_ids_in_mask, _, _ = tilestore.get_tile_ids_intersecting_mask(image_id, annotation_class_id)
            tile_ids_in_bbox_and_mask = set(tile_ids_in_bbox) & set(tile_ids_in_mask)
        else:
            tile_ids_in_bbox_and_mask = tile_ids_in_bbox

        # Filter by tiles which have ground truths saved. This limits the number of tiles we have to consider for rendering.
        if args['hasgt']:
            tiles = tilestore.get_tiles_by_tile_ids(image_id, annotation_class_id, tile_ids_in_bbox_and_mask, hasgt=True)
            tile_ids_in_bbox_and_mask = [tile.tile_id for tile in tiles]

        tile_refs = [{"tile_id": tile_id, "downsampled_tile_id": tilespace.downsample_tile_id(tile_id, downsample_level)} for tile_id in tile_ids_in_bbox_and_mask]
        return tile_refs, 200

@bp.route('/<int:image_id>/<int:annotation_class_id>/search/polygon')
class TileIdSearchByPolygon(MethodView):
    @bp.arguments(server_models.SearchTileByPolygonArgsSchema, location='json')
    @bp.response(200, server_models.TileRefRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     get all Tiles within a polygon
        """
        tilestore = TileStoreFactory.get_tilestore()
        tilespace = get_tilespace(image_id=image_id, annotation_class_id=annotation_class_id, in_work_mag=False)
        tiles_in_polygon, _, _ = tilestore.get_tile_ids_intersecting_polygons(image_id, annotation_class_id, [args['polygon']], mask_dilation=1)

        if annotation_class_id != MASK_CLASS_ID:
            tile_ids_in_mask, _, _ = tilestore.get_tile_ids_intersecting_mask(image_id, annotation_class_id)
            tile_ids_in_poly_and_mask = set(tiles_in_polygon) & set(tile_ids_in_mask)
        else:
            tile_ids_in_poly_and_mask = tiles_in_polygon

        if args['hasgt']:
            tiles = tilestore.get_tiles_by_tile_ids(image_id, annotation_class_id, tile_ids_in_poly_and_mask, hasgt=True)
            tile_ids_in_poly_and_mask = [tile.tile_id for tile in tiles]

        tile_refs = [{"tile_id": tile_id, "downsampled_tile_id": tilespace.downsample_tile_id(tile_id, args.get('downsample_level', 0))} for tile_id in tile_ids_in_poly_and_mask]
        return tile_refs, 200

@bp.route('/<int:image_id>/<int:annotation_class_id>/search/coordinates')
class TileIdSearchByCoordinates(MethodView):
    @bp.arguments(server_models.SearchTileByCoordinatesArgsSchema, location='query')
    @bp.response(200, server_models.TileRefRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     get a Tile for a given point
        """
        tilespace = get_tilespace(image_id=image_id, annotation_class_id=annotation_class_id, in_work_mag=False)
        tile_id = tilespace.point_to_tileid(args['x'], args['y'])
        tile_ref = {"tile_id": tile_id, "downsampled_tile_id": tilespace.downsample_tile_id(tile_id, args.get('downsample_level', 0))}
        return tile_ref, 200
