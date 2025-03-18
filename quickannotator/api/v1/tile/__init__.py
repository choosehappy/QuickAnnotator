from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from ..utils.shared_crud import upsert_tiles
import quickannotator.db as qadb
from quickannotator.db import db_session
from quickannotator.constants import TileStatus
import quickannotator.db.models as models
from .helper import get_tile, compute_on_tile, get_tile_ids_intersecting_mask, get_tile_ids_intersecting_polygons
from quickannotator.api.v1.utils.coordinate_space import get_tilespace
bp = Blueprint('tile', __name__, description="Tile operations")

# ------------------------ RESPONSE MODELS ------------------------
class TileRespSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.Tile
        include_fk = True

class PredictTileRespSchema(Schema):
    object_ref = fields.Str()
    message = fields.Str()

class TileBoundingBoxRespSchema(Schema):
    bbox = fields.Tuple((fields.Int, fields.Int, fields.Int, fields.Int))

class TileIdRespSchema(Schema):
    tileids = fields.List(fields.Int)
# ------------------------ REQUEST PARSERS ------------------------
class GetTileArgsSchema(Schema):
    tile_id = fields.Int(description="ID of the tile")

class PostTileArgsSchema(GetTileArgsSchema):
    pass

class SearchTileArgsSchema(Schema):
    hasgt = fields.Bool(required=True, description="Filter by tiles which have ground truths saved")
    x1 = fields.Float(required=True, description="X-coordinate of the top-left corner of the bounding box")
    y1 = fields.Float(required=True, description="Y-coordinate of the top-left corner of the bounding box")
    x2 = fields.Float(required=True, description="X-coordinate of the bottom-right corner of the bounding box")
    y2 = fields.Float(required=True, description="Y-coordinate of the bottom-right corner of the bounding box")

class SearchTileByPolygonArgsSchema(Schema):
    hasgt = fields.Bool(required=True, description="Filter by tiles which have ground truths saved")
    polygon = models.GeometryField(required=True, description="Polygon geometry to search within")

class SearchTileByCoordinatesArgsSchema(Schema):
    x = fields.Float(required=True, description="X-coordinate of the point")
    y = fields.Float(required=True, description="Y-coordinate of the point")

# ------------------------ ROUTES ------------------------

@bp.route('/<int:image_id>/<int:annotation_class_id>')
class Tile(MethodView):
    @bp.arguments(GetTileArgsSchema, location='query')
    @bp.response(200, TileRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     returns a Tile
        """
        result = get_tile(image_id, annotation_class_id, args['tile_id'])
        return result, 200

    @bp.arguments(PostTileArgsSchema, location='query')
    @bp.response(200, description="Staged tile for DL processing")
    def post(self, args, image_id, annotation_class_id):
        """     stage a tile for DL processing     """
        
        upsert_tiles(image_id, annotation_class_id, [args['tile_id']], pred_status=TileStatus.STARTPROCESSING)
        return 200


    @bp.arguments(GetTileArgsSchema, location='query')
    def delete(self, args, image_id, annotation_class_id):
        """     delete a Tile
        """
        tile = db_session.query(models.Tile).filter_by(
            image_id=image_id,
            annotation_class_id=annotation_class_id,
            tile_id=args['tile_id']
        ).first()
        if tile:
            db_session.delete(tile)
            db_session.commit()
        return 204

@bp.route('/<int:image_id>/<int:annotation_class_id>/bbox')
class TileBoundingBox(MethodView):
    @bp.arguments(GetTileArgsSchema, location='query')
    @bp.response(200, TileBoundingBoxRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     get the bounding box for a given tile
        """
        tilespace = get_tilespace(image_id=image_id, annotation_class_id=annotation_class_id, in_work_mag=False)
        bbox = tilespace.get_bbox_for_tile(args['tile_id'])
        return {'bbox': bbox}, 200

@bp.route('/<int:image_id>/<int:annotation_class_id>/search/bbox')
class TileIdSearchByBbox(MethodView):
    @bp.arguments(SearchTileArgsSchema, location='query')
    @bp.response(200, TileIdRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     get all Tiles within a bounding box
        """
        tilespace = get_tilespace(image_id=image_id, annotation_class_id=annotation_class_id, in_work_mag=False)
        tile_ids_in_bbox = tilespace.get_tile_ids_within_bbox((args['x1'], args['y1'], args['x2'], args['y2']))
        tile_ids_in_mask, _, _ = get_tile_ids_intersecting_mask(image_id, annotation_class_id, mask_dilation=1)
        ids = set(tile_ids_in_bbox) & set(tile_ids_in_mask)

        # Filter by tiles which have ground truths saved. This limits the number of tiles we have to consider for rendering.
        if args['hasgt']:
            ids = db_session.query(models.Tile.tile_id).filter(
                models.Tile.annotation_class_id == annotation_class_id,
                models.Tile.image_id == image_id,
                models.Tile.tile_id.in_(ids),
                models.Tile.gt_datetime.isnot(None)
            ).all()
            ids = [id[0] for id in ids]
        return {"tileids": ids}, 200
    
@bp.route('/<int:image_id>/<int:annotation_class_id>/search/polygon')
class TileIdSearchByPolygon(MethodView):
    @bp.arguments(SearchTileByPolygonArgsSchema, location='json')
    @bp.response(200, TileIdRespSchema)
    def post(self, args, image_id, annotation_class_id):
        """     get all Tiles within a polygon
        """
        tiles_in_polygon, _, _ = get_tile_ids_intersecting_polygons(image_id, annotation_class_id, [args['polygon']], mask_dilation=1)
        tile_ids_in_mask, _, _ = get_tile_ids_intersecting_mask(image_id, annotation_class_id, mask_dilation=1)
        ids = set(tiles_in_polygon) & set(tile_ids_in_mask)

        if args['hasgt']:
            ids = db_session.query(models.Tile.tile_id).filter(
                models.Tile.annotation_class_id == annotation_class_id,
                models.Tile.image_id == image_id,
                models.Tile.tile_id.in_(ids),
                models.Tile.gt_datetime.isnot(None)
            ).all()
            ids = [id[0] for id in ids]
        return {"tileids": ids}, 200

    
@bp.route('/<int:image_id>/<int:annotation_class_id>/search/coordinates')
class TileIdSearchByCoordinates(MethodView):
    @bp.arguments(SearchTileByCoordinatesArgsSchema, location='query')
    @bp.response(200, TileIdRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     get a Tile for a given point
        """
        tilespace = get_tilespace(image_id=image_id, annotation_class_id=annotation_class_id, in_work_mag=False)
        tile_id = tilespace.point_to_tileid(args['x'], args['y'])
        return {"tileids": [tile_id]}, 200