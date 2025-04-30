from marshmallow import fields, Schema
import quickannotator.constants as constants


class ProjectRespSchema(Schema):
    """     Project response schema      """
    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    date = fields.DateTime(format=constants.FLASK_DATETIME_FORMAT)


class GetProjectArgsSchema(Schema):
    project_id = fields.Int(required=True)
    

class PostProjectArgsSchema(Schema):
    name = fields.Str(required=True)
    is_dataset_large = fields.Bool(required=False)
    description = fields.Str(required=True)
    

class PutProjectArgsSchema(Schema):
    project_id = fields.Int(required=True)
    name = fields.Str(required=False)
    is_dataset_large = fields.Bool(required=False)
    description = fields.Str(required=False)
    

class DeleteProjectArgsSchema(GetProjectArgsSchema):
    pass


class SearchProjectArgsSchema(Schema):
    name = fields.Str(required=False)