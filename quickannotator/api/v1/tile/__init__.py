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
    annotation_class_id = fields.Int()
    image_id = fields.Int()
    tile_id = fields.Int()

class PutTileArgsSchema(Schema):
    seen = fields.Int()

class PostTileArgsSchema(Schema):
    image_id = fields.Int(required=True)
    annotation_class_id = fields.Int(required=True)

class SearchTileArgsSchema(Schema):
    image_id = fields.Int(required=True)
    annotation_class_id = fields.Int(required=True)
    hasgt = fields.Bool(required=False)
    x1 = fields.Float(required=True)
    y1 = fields.Float(required=True)
    x2 = fields.Float(required=True)
    y2 = fields.Float(required=True)

class SearchTileByPolygonArgsSchema(Schema):
    image_id = fields.Int(required=True)
    annotation_class_id = fields.Int(required=True)
    hasgt = fields.Bool(required=False)
    polygon = models.GeometryField(required=True)

class SearchTileByCoordinatesArgsSchema(Schema):
    image_id = fields.Int(required=True)
    annotation_class_id = fields.Int(required=True)
    x = fields.Float(required=True)
    y = fields.Float(required=True)

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
        result = get_tile(args['annotation_class_id'], args['image_id'], args['tile_id'])
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

        if args['hasgt']:
            ids = db_session.query(models.Tile.id).filter(
                models.Tile.id.in_(ids),
                models.Tile.hasgt.is_(True)
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
                models.Tile.hasgt.is_(True)
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

@bp.route('/predict')
class TilePredict(MethodView):
    @bp.arguments(PredictTileArgsSchema, location='json')
    @bp.response(201, PredictTileRespSchema)
    def post(self, args):
        """     predict tiles for a given image & class
        """
        upsert_tiles(args['annotation_class_id'], args['image_id'], [args['tile_id']], seen=TileStatus.PROCESSING)

        object_ref = compute_on_tile(args['annotation_class_id'], args['image_id'], tile_id=args['tile_id'], sleep_time=5)
        return {'object_ref': object_ref}, 201
        
