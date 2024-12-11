from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from pkg_resources import require

import quickannotator.db as qadb
from quickannotator.db import db
from .helper import tiles_within_bbox, generate_random_circle_within_bbox, tile_by_id, compute_on_tile

bp = Blueprint('tile', __name__, description="Tile operations")

# ------------------------ RESPONSE MODELS ------------------------
class TileRespSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = qadb.Tile
        include_fk = True

    geom = qadb.GeometryField()

class PredictTileRespSchema(Schema):
    job_id = fields.Int()

# ------------------------ REQUEST PARSERS ------------------------
class GetTileArgsSchema(Schema):
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
        result = db.session.query(
            *[getattr(qadb.Tile, column.name) for column in qadb.Tile.__table__.columns],
            db.func.ST_AsGeoJSON(qadb.Tile.geom).label('geom')
        ).filter_by(id=args['tile_id']).first()
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
    

@bp.route('/predict')
class TilePredict(MethodView):
    @bp.arguments(PredictTileArgsSchema, location='json')
    @bp.response(201, PredictTileRespSchema)
    def post(self, args):
        """     predict tiles for a given image & class
        """
        # Update the Tile seen column to 1
        tile = tile_by_id(db, args['tile_id'])
        tile.seen = 1
        db.session.commit()

        job_id = compute_on_tile(db=db, qadb=qadb, tile_id=args['tile_id'], sleep_time=5)

        return {'job_id': job_id}, 201
        
