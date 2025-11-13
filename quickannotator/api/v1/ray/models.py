from marshmallow import fields, Schema


class RayClusterStateFilters(Schema):
    # A list of 3-tuples (field, operator, value) used by ray.util.state.list_tasks
    rayClusterFilters = fields.List(fields.Tuple((fields.Str(), fields.Str(), fields.Str())), required=False)


class RayTaskState(Schema):
    taskId = fields.Str(required=True)
    funcOrClassName = fields.Str(required=True)
    state = fields.Str(required=True)
    # The routes return creation/end times as milliseconds (integers).
    creationTime = fields.Integer(required=False, allow_none=True)
    endTime = fields.Integer(required=False, allow_none=True)
    errorMessage = fields.Str(required=False, allow_none=True)

