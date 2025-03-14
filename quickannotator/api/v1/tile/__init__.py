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
    tile_ids = fields.List(fields.Int)
# ------------------------ REQUEST PARSERS ------------------------
class GetTileArgsSchema(Schema):
    annotation_class_id = fields.Int(description="ID of the annotation class")
    image_id = fields.Int(description="ID of the image")
    tile_id = fields.Int(description="ID of the tile")

class PutTileArgsSchema(Schema):
    seen = fields.Int(description="Seen status of the tile")

class PostTileArgsSchema(Schema):
    image_id = fields.Int(required=True, description="ID of the image")
    annotation_class_id = fields.Int(required=True, description="ID of the annotation class")

class SearchTileArgsSchema(Schema):
    image_id = fields.Int(required=True, description="ID of the image")
    annotation_class_id = fields.Int(required=True, description="ID of the annotation class")
    hasgt = fields.Bool(required=True, description="Filter by tiles which have ground truths saved")
    x1 = fields.Float(required=True, description="X-coordinate of the top-left corner of the bounding box")
    y1 = fields.Float(required=True, description="Y-coordinate of the top-left corner of the bounding box")
    x2 = fields.Float(required=True, description="X-coordinate of the bottom-right corner of the bounding box")
    y2 = fields.Float(required=True, description="Y-coordinate of the bottom-right corner of the bounding box")

class SearchTileByPolygonArgsSchema(Schema):
    image_id = fields.Int(required=True, description="ID of the image")
    annotation_class_id = fields.Int(required=True, description="ID of the annotation class")
    hasgt = fields.Bool(required=False, description="Filter by tiles which have ground truths saved")
    polygon = models.GeometryField(required=True, description="Polygon geometry to search within")

class SearchTileByCoordinatesArgsSchema(Schema):
    image_id = fields.Int(required=True, description="ID of the image")
    annotation_class_id = fields.Int(required=True, description="ID of the annotation class")
    x = fields.Float(required=True, description="X-coordinate of the point")
    y = fields.Float(required=True, description="Y-coordinate of the point")

class PredictTileArgsSchema(GetTileArgsSchema):
    pass
# ------------------------ ROUTES ------------------------

@bp.route('')
class Tile(MethodView):
    @bp.arguments(GetTileArgsSchema, location='query')
    @bp.response(200, TileRespSchema)
    def get(self, args):
        """     returns a Tile
        """
        result = get_tile(args['image_id'], args['annotation_class_id'], args['tile_id'])
        return result, 200

    @bp.arguments(PostTileArgsSchema, location='query')
    @bp.response(200, description="Successfully computed tiles")
    def post(self, args):
        """     compute all tiles for a given image & class     """

        return 200

    @bp.arguments(PutTileArgsSchema, location='query')
    @bp.response(201, description="Successfully updated tile.")
    def put(self):
        """     update a Tile

        """

        return 201

    def delete(self):
        """     delete a Tile

        """

        return 204

@bp.route('/bbox')
class TileBoundingBox(MethodView):
    @bp.arguments(GetTileArgsSchema, location='query')
    @bp.response(200, TileBoundingBoxRespSchema)
    def get(self, args):
        """     get the bounding box for a given tile
        """
        tilespace = get_tilespace(image_id=args['image_id'], annotation_class_id=args['annotation_class_id'], in_work_mag=False)
        bbox = tilespace.get_bbox_for_tile(args['tile_id'])
        return {'bbox': bbox}, 200

@bp.route('/search/bbox')
class TileIdSearch(MethodView):
    @bp.arguments(SearchTileArgsSchema, location='query')
    @bp.response(200, TileIdRespSchema)
    def get(self, args):
        """     get all Tiles within a bounding box
        """
        
        tilespace = get_tilespace(image_id=args['image_id'], annotation_class_id=args['annotation_class_id'], in_work_mag=False)
        tile_ids_in_bbox = tilespace.get_tile_ids_within_bbox((args['x1'], args['y1'], args['x2'], args['y2']))
        tile_ids_in_mask, _, _ = get_tile_ids_intersecting_mask(args['image_id'], args['annotation_class_id'], mask_dilation=1)
        ids = set(tile_ids_in_bbox) & set(tile_ids_in_mask)

        # Filter by tiles which have ground truths saved. This limits the number of tiles we have to consider for rendering.
        if args['hasgt']:
            ids = db_session.query(models.Tile.id).filter(
                models.Tile.id.in_(ids),
                models.Tile.gt_datetime.isnot(None)
            ).all()
            ids = [id[0] for id in ids]
        return ids, 200
    
@bp.route('/search/polygon')
class TileIdSearchByPolygon(MethodView):
    @bp.arguments(SearchTileByPolygonArgsSchema, location='json')
    @bp.response(200, TileIdRespSchema)
    def post(self, args):
        """     get all Tiles within a polygon
        """
        tiles_in_polygon, _, _ = get_tile_ids_intersecting_polygons(args['image_id'], args['annotation_class_id'], [args['polygon']], mask_dilation=1)
        tile_ids_in_mask, _, _ = get_tile_ids_intersecting_mask(args['image_id'], args['annotation_class_id'], mask_dilation=1)
        ids = set(tiles_in_polygon) & set(tile_ids_in_mask)

        if args['hasgt']:
            ids = db_session.query(models.Tile.id).filter(
                models.Tile.id.in_(ids),
                models.Tile.gt_datetime.isnot(None)
            ).all()
            ids = [id[0] for id in ids]
        return ids, 200

    
@bp.route('/search/coordinates')
class TileIdSearchByCoordinates(MethodView):
    @bp.arguments(SearchTileByCoordinatesArgsSchema, location='query')
    @bp.response(200, TileRespSchema)
    def get(self, args):
        """     get a Tile for a given point
        """
        tilespace = get_tilespace(image_id=args['image_id'], annotation_class_id=args['annotation_class_id'], in_work_mag=False)
        tile_id = tilespace.point_to_tileid(args['x'], args['y'])
        return tile_id, 200
        