from ray.util.state.common import TaskState

def convert_ray_task_to_dict(task: TaskState) -> dict:
    """
    Utility method to convert a Ray task object to a dictionary.
    """
    return {
        "task_id": task.task_id,
        "func_or_class_name": task.func_or_class_name,
        "state": task.state,
        "creation_time": task.creation_time_ms,
        "end_time": task.end_time_ms,
        "error_message": task.error_message
    }