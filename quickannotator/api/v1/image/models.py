from flask_smorest.fields import Upload
from marshmallow import fields, Schema, ValidationError, validates
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from html.parser import HTMLParser

import quickannotator.db.models as db_models


class HTMLTagDetector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.has_tags = False

    def handle_starttag(self, tag, attrs):
        self.has_tags = True

    def handle_endtag(self, tag):
        self.has_tags = True


def contains_html_tags(html_string: str) -> bool:
    detector = HTMLTagDetector()
    detector.feed(html_string)
    return detector.has_tags

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
    folder_name: str | None = fields.String(load_default=None, allow_none=True)

class UpdateImageCommentSchema(Schema):
    comment = fields.Str(required=True)

    @validates("comment")
    def validate_comment(self, data):
        if contains_html_tags(data):
            raise ValidationError("HTML content is not allowed")

class ImageMetadataRespSchema(Schema):
    mpp = fields.Float()