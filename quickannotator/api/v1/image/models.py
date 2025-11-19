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
    ray_task_id = fields.Str(required=True)
    name = fields.Str(required=True)
    type = fields.Str(required=True)

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