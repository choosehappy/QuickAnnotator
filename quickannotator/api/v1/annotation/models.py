from marshmallow import fields, Schema, ValidationError
import quickannotator.db.models as db_models
import quickannotator.constants as constants

class AnnRespSchema(Schema):
    """     Annotation response schema      """
    id = fields.Int()
    tile_id = fields.Int()
    centroid = db_models.GeometryField()
    polygon = db_models.GeometryField()
    area = fields.Float()
    custom_metrics = fields.Dict()

    datetime = fields.DateTime(format=constants.FLASK_DATETIME_FORMAT)

class ActorRespSchema(Schema):
    actor_name = fields.Str()

class ExportServerRespSchema(ActorRespSchema):
    """     Download link schema      """
    filepaths = fields.List(fields.Str())

class GetAnnBaseArgsSchema(Schema):
    simplify_tolerance = fields.Float(required=False, missing=0.0)

class GetAnnArgsSchema(GetAnnBaseArgsSchema):
    is_gt = fields.Bool(required=True)
    annotation_id = fields.Int(required=True)

class GetAnnSearchArgsSchema(GetAnnBaseArgsSchema):
    is_gt = fields.Bool(required=True)
    x1 = fields.Int(required=False)
    y1 = fields.Int(required=False)
    x2 = fields.Int(required=False)
    y2 = fields.Int(required=False)
    polygon = db_models.GeometryField(required=False)

class GetAnnWithinPolyArgsSchema(GetAnnBaseArgsSchema):
    is_gt = fields.Bool(required=True)
    polygon = db_models.GeometryField(required=True)

class GetAnnByTileIdsArgsSchema(GetAnnBaseArgsSchema):
    tile_ids = fields.List(fields.Int(), required=True)
    is_gt = fields.Bool(required=True)

class PostAnnsArgsSchema(Schema):
    polygons = fields.List(db_models.GeometryField(), required=True)

class OperationArgsSchema(AnnRespSchema):
    operation = fields.Integer(required=True)  # Default 0 for union.
    polygon2 = db_models.GeometryField(required=True)    # The second polygon

class PutAnnArgsSchema(Schema):
    annotation_id = fields.Int(required=True)
    polygon = db_models.GeometryField(required=True)
    is_gt = fields.Bool(required=True)

class DeleteAnnArgsSchema(GetAnnArgsSchema):
    pass

class PostDryRunArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    polygon = fields.String(required=True)
    script = fields.Str(required=True)

def validate_non_empty_list(value):
    if not value:
        raise ValidationError("List cannot be empty.")
    
class GetAnnsByImageAndAnnotationClassIds(Schema):
    image_ids = fields.List(
        fields.Int(),
        required=True,
        validate=validate_non_empty_list
    )
    annotation_class_ids = fields.List(
        fields.Int(),
        required=True,
        validate=validate_non_empty_list
    )
    
class ExportToServerSchema(GetAnnsByImageAndAnnotationClassIds):
    export_formats = fields.List(
        fields.Enum(constants.AnnsFormatEnum),
        required=True,
        validate=validate_non_empty_list,
        default=[constants.AnnsFormatEnum.GEOJSON]
    )

class ExportToDSASchema(GetAnnsByImageAndAnnotationClassIds):
    api_uri = fields.Str(required=True)
    api_key = fields.Str(required=True)
    folder_id = fields.Str(required=True)

class ErrorRespSchema(Schema):
    """Schema for error responses."""
    message = fields.Str(required=True)
