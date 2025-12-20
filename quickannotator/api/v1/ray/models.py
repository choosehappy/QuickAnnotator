from marshmallow import fields, Schema


class RayClusterStateFilters(Schema):
    """
    RayClusterStateFilters schema for specifying filters to query Ray cluster state.

    Attributes:
        ray_cluster_filters (list of tuple): A list of 3-tuples where each tuple contains:
            - field (str): The name of the field to filter on.
            - operator (str): The comparison operator to use (e.g., '=', '!=', '<', etc.).
            - value (str): The value to compare the field against.

    Note:
        The filters should match the format and fields described in the Ray documentation:
        https://docs.ray.io/en/latest/ray-observability/reference/doc/ray.util.state.list_tasks.html
    """
    # A list of 3-tuples (field, operator, value) used by ray.util.state.list_tasks
    ray_cluster_filters = fields.List(fields.Tuple((fields.Str(), fields.Str(), fields.Str())), required=False)


class RayTaskState(Schema):
    task_id = fields.Str(required=True)
    func_or_class_name = fields.Str(required=True)
    state = fields.Str(required=True)
    # The routes return creation/end times as milliseconds (integers).
    creation_time = fields.Integer(required=False, allow_none=True)
    end_time = fields.Integer(required=False, allow_none=True)
    error_message = fields.Str(required=False, allow_none=True)

class GetRayTasksArgsSchema(Schema):
    by_parent_task_id = fields.Str(required=False, description="Parent task ID to filter tasks by.")

class SetEnableDLArgsSchema(Schema):
    value = fields.Bool(required=True, description="Boolean value to enable (true) or disable (false) deep learning training.")