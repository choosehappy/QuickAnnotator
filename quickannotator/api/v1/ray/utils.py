from ray.util.state.common import TaskState

def convert_ray_task_to_dict(task: TaskState) -> dict:
    """
    Utility method to convert a Ray task object to a dictionary.
    """
    return {
        "taskId": task.task_id,
        "funcOrClassName": task.func_or_class_name,
        "state": task.state,
        "creationTime": task.creation_time_ms,
        "endTime": task.end_time_ms,
        "errorMessage": task.error_message
    }