from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from pkg_resources import require

import quickannotator.db as qadb
from quickannotator.db import db
from quickannotator.db import Image, AnnotationClass
from .helper import get_tile, compute_on_tile, upsert_tile, get_tile_ids_within_bbox, get_tile_id_for_point
from quickannotator.api.v1.image.helper import get_image_by_id
from quickannotator.api.v1.annotation_class.helper import get_annotation_class_by_id

bp = Blueprint('tile', __name__, description="Tile operations")

# ------------------------ RESPONSE MODELS ------------------------
class TileRespSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = qadb.Tile
        include_fk = True

class PredictTileRespSchema(Schema):
    object_ref = fields.Str()

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
    x1 = fields.Float(required=True)
    y1 = fields.Float(required=True)
    x2 = fields.Float(required=True)
    y2 = fields.Float(required=True)

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
        result = get_tile(db.session, args['annotation_class_id'], args['image_id'], args['tile_id'])
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

@bp.route('/search/bbox')
class TileSearch(MethodView):
    @bp.arguments(SearchTileArgsSchema, location='query')
    @bp.response(200, TileRespSchema(many=True))
    def get(self, args):
        """     get all Tiles within a bounding box
        """
        image: Image = get_image_by_id(args['image_id'])
        annotation_class: AnnotationClass = get_annotation_class_by_id(args['annotation_class_id'])
        tile_ids = get_tile_ids_within_bbox(annotation_class.tilesize, (args['x1'], args['y1'], args['x2'], args['y2']), image.width, image.height)
        tiles = qadb.db.session.query(qadb.Tile).filter(qadb.Tile.id.in_(tile_ids)).all()
        
        return tiles, 200
    
@bp.route('/search/coordinates')
class TileSearchByCoordinates(MethodView):
    @bp.arguments(SearchTileArgsSchema, location='query')
    @bp.response(200, TileRespSchema)
    def get(self, args):
        """     get a Tile for a given point
        """
        image: Image = get_image_by_id(args['image_id'])
        annotation_class: AnnotationClass = get_annotation_class_by_id(args['annotation_class_id'])
        tile_id = get_tile_id_for_point(annotation_class.tilesize, (args['x'], args['y']), image.width, image.height)
        return get_tile(db.session, args['annotation_class_id'], args['image_id'], tile_id), 200

@bp.route('/predict')
class TilePredict(MethodView):
    @bp.arguments(PredictTileArgsSchema, location='json')
    @bp.response(201, PredictTileRespSchema)
    def post(self, args):
        """     predict tiles for a given image & class
        """
        upsert_tile(args['annotation_class_id'], args['image_id'], args['tile_id'], seen=1)

        object_ref = compute_on_tile(db=db, tile_id=args['tile_id'], sleep_time=5)

        return {'object_ref': object_ref}, 201
        
