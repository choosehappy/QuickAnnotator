def build_ray_cluster_filters(task_id) -> list[tuple[str, str, str]]:
    return [("parent_task_id", "=", task_id)]

