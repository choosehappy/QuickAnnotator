from flask_smorest import Blueprint
from quickannotator import constants
from quickannotator.api.v1.ray.utils import convert_ray_task_to_dict
from . import models as server_models
from flask.views import MethodView
import ray
from ray.util.state.common import TaskState
from ray.util import state

bp = Blueprint('ray', __name__, description='Ray operations')

@bp.route('/task/<string:task_id>', endpoint='ray_task')
class RayTaskByIdResource(MethodView):
    @bp.response(200, server_models.RayTaskState)
    def get(self, task_id):
        """
        Handle GET requests to retrieve Ray task information by task ID.
        """
        try:
            task_info = state.get_task(task_id)
            if task_info:
                return convert_ray_task_to_dict(task_info), 200
            else:
                return {"message": "Task not found"}, 404
        except Exception as e:
            return {"message": f"Error retrieving task: {str(e)}"}, 500


@bp.route('/task', endpoint='ray_tasks')
class RayTasksResource(MethodView):
    @bp.arguments(server_models.RayClusterStateFilters, location='json')
    @bp.response(200, server_models.RayTaskState(many=True))
    def post(self, args):
        """
        Handle POST requests to retrieve Ray task information based on filters. See https://docs.ray.io/en/latest/ray-observability/reference/doc/ray.util.state.list_tasks.html for more information.
        """
        filters = args.get('ray_cluster_filters', [])
        
        # Fetch tasks from Ray state with the provided filters
        try:
            tasks: list[TaskState] = state.list_tasks(filters=filters, detail=True, limit=constants.RAY_TASK_RETURN_LIMIT)
            task_states = [convert_ray_task_to_dict(task) for task in tasks]
            return task_states, 200
        except Exception as e:
            return {"message": f"Error retrieving tasks: {str(e)}"}, 500
