from flask_smorest.fields import Upload
from marshmallow import fields, Schema
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

import quickannotator.db.models as db_models

class ImageRespSchema(SQLAlchemyAutoSchema):
    """     Image response schema      """
    class Meta:
        model = db_models.Image

    embedding_coord = db_models.GeometryField()

class GetImageArgsSchema(Schema):
    image_id = fields.Int(required=True)


class UploadFileSchema(Schema):
    name = fields.Str(required=True)
    type = fields.Str(required=True)
    ray_cluster_filters = fields.List(fields.Tuple(fields.Str(), fields.Str(), fields.Str()), required=False)

class SearchImageArgsSchema(Schema):
    pass

class PostImageArgsSchema(Schema):
    name = fields.Str(required=True)
    path = fields.Str(required=True)
    embedding_coord = fields.Str(required=False)
    group_id = fields.Int(required=False)
    split = fields.Int(required=False)

class DeleteImageArgsSchema(GetImageArgsSchema):
    pass

class UploadFileArgsSchema(Schema):
    project_id = fields.Int(required=True)

class ImageMetadataRespSchema(Schema):
    mpp = fields.Float()