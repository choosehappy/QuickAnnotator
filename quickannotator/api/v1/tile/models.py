from marshmallow import fields, Schema
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import quickannotator.db.models as db_models


class TileRespSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = db_models.Tile
        include_fk = True


class PredictTileRespSchema(Schema):
    object_ref = fields.Str()
    message = fields.Str()


class TileBoundingBoxRespSchema(Schema):
    bbox_polygon = db_models.GeometryField()


class TileIdRespSchema(Schema):
    tile_ids = fields.List(fields.Int)


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
    polygon = db_models.GeometryField(required=True, description="Polygon geometry to search within")


class SearchTileByCoordinatesArgsSchema(Schema):
    x = fields.Float(required=True, description="X-coordinate of the point")
    y = fields.Float(required=True, description="Y-coordinate of the point")