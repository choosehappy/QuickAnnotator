from marshmallow import fields, Schema
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import quickannotator.db.models as db_models


class TileRespSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = db_models.Tile
        include_fk = True


class PredictTileRespSchema(TileRespSchema):
    bbox_polygon = db_models.GeometryField(metadata={"description": "Bounding box polygon of the tile. Present only if include_bbox is True."})


class TileBoundingBoxRespSchema(Schema):
    tile_id = fields.Int()
    bbox_polygon = db_models.GeometryField()


class TileRefRespSchema(Schema):
    tile_id = fields.Int()
    downsampled_tile_id = fields.Int()


class BaseTileArgsSchema(Schema):
    downsample_level = fields.Int(required=False, description="The level to group tiles by. Zero means no downsampling")


class GetTileArgsSchema(BaseTileArgsSchema):
    tile_id = fields.Int(description="ID of the tile")
    

class PostTileArgsSchema(Schema):
    tile_ids = fields.List(fields.Int(), required=True, description="List of tile IDs to process")
    include_bbox = fields.Bool(required=False, missing=False, description="Whether to include bounding box polygons in the response")

class SearchTileArgsSchema(BaseTileArgsSchema):
    hasgt = fields.Bool(required=True, description="Filter by tiles which have ground truths saved")
    x1 = fields.Float(required=True, description="X-coordinate of the top-left corner of the bounding box")
    y1 = fields.Float(required=True, description="Y-coordinate of the top-left corner of the bounding box")
    x2 = fields.Float(required=True, description="X-coordinate of the bottom-right corner of the bounding box")
    y2 = fields.Float(required=True, description="Y-coordinate of the bottom-right corner of the bounding box")


class SearchTileByPolygonArgsSchema(BaseTileArgsSchema):
    hasgt = fields.Bool(required=True, description="Filter by tiles which have ground truths saved")
    polygon = db_models.GeometryField(required=True, description="Polygon geometry to search within")


class SearchTileByCoordinatesArgsSchema(BaseTileArgsSchema):
    x = fields.Float(required=True, description="X-coordinate of the point")
    y = fields.Float(required=True, description="Y-coordinate of the point")