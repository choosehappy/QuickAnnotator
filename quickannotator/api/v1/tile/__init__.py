from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from pkg_resources import require

import quickannotator.db as qadb
from quickannotator.db import db
from .helper import tiles_within_bbox

bp = Blueprint('tile', __name__, description="Tile operations")

# ------------------------ RESPONSE MODELS ------------------------
class TileRespSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = qadb.Tile
        include_fk = True

    geom = qadb.GeometryField()


# ------------------------ REQUEST PARSERS ------------------------
class GetTileArgsSchema(Schema):
    tile_id = fields.Str()

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


# ------------------------ ROUTES ------------------------

@bp.route('')
class Tile(MethodView):
    @bp.arguments(GetTileArgsSchema, location='query')
    @bp.response(200, TileRespSchema)
    def get(self, args):
        """     returns a Tile
        """
        result = db.session.query(qadb.Tile).filter_by(id=args['tile_id']).first()
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

@bp.route('/search')
class TileSearch(MethodView):
    @bp.arguments(SearchTileArgsSchema, location='query')
    @bp.response(200, TileRespSchema(many=True))
    def get(self, args):
        """     get all Tiles within a bounding box
        """
        tiles = tiles_within_bbox(db, args['image_id'], args['annotation_class_id'], args['x1'], args['y1'], args['x2'], args['y2'])
        return tiles, 200