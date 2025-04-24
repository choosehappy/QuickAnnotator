from marshmallow import fields, Schema
import quickannotator.db.models as db_models
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

class AnnClassRespSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = db_models.AnnotationClass


class GetAnnClassArgsSchema(Schema):
    annotation_class_id = fields.Int(required=True)

class PostAnnClassArgsSchema(Schema):
    project_id = fields.Int(required=True)
    name = fields.Str(required=True)
    color = fields.Str(required=True)
    work_mag = fields.Int(required=True)

class PutAnnClassArgsSchema(GetAnnClassArgsSchema):
    name = fields.Str(required=False)
    color = fields.Str(required=False)

class SearchAnnClassArgsSchema(Schema):
    name = fields.Str(required=False)
    project_id = fields.Int(required=False)
