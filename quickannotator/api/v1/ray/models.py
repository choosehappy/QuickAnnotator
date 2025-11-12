from marshmallow import fields, Schema

class RayClusterStateFilters(Schema):
    ray_cluster_filters = fields.List(fields.Tuple((fields.Str(), fields.Str(), fields.Str())), required=False)

class RayTaskState(Schema):
    taskId = fields.Str(required=True)
    funcOrClassName = fields.Str(required=True)
    state = fields.Str(required=True)
    creationTime = fields.DateTime(required=True)
    endTime = fields.DateTime(required=True)
    errorMessage = fields.Str(required=True)


class RayTaskStateResponse(Schema):
    taskStates = fields.List(fields.Nested(RayTaskState))

