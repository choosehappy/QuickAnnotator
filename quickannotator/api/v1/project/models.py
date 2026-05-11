from marshmallow import fields, Schema
import quickannotator.constants as constants


class ProjectRespSchema(Schema):
    """     Project response schema      """
    id = fields.Int()
    name = fields.Str()
    is_dataset_large = fields.Bool(required=False)
    description = fields.Str()
    datetime = fields.DateTime(format=constants.FLASK_DATETIME_FORMAT)


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


class StatsCountSchema(Schema):
    count = fields.Int()


class AnnotationStatRespSchema(Schema):
    group_id = fields.Int()
    group_label = fields.Str()
    stats = fields.Nested(StatsCountSchema)


class ProjectAnnotationStatsArgsSchema(Schema):
    group_by = fields.Str(
        load_default='annotation_class',
        metadata={"description": "Group results by 'annotation_class' or 'image'"}
    )
    annotation_class_ids = fields.Str(
        load_default=None,
        metadata={"description": "Comma-separated list of annotation class IDs to filter by"}
    )
    image_ids = fields.Str(
        load_default=None,
        metadata={"description": "Comma-separated list of image IDs to filter by"}
    )


class ProjectCountRespSchema(Schema):
    stats = fields.Nested(StatsCountSchema)
