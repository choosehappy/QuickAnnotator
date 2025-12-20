from flask_smorest import Blueprint, error_handler
from flask import abort
from quickannotator import constants
from quickannotator.api.v1.ray.utils import convert_ray_task_to_dict
from . import models as server_models
from flask.views import MethodView
import ray
from ray.util.state.common import TaskState
from ray.util import state
from ray.util.state.exception import ServerUnavailable
from quickannotator.db.crud.annotation_class import build_actor_name

bp = Blueprint('ray', __name__, description='Ray operations')

@bp.route('/task/<string:task_id>', endpoint='ray_task')
class RayTaskByIdResource(MethodView):
    @bp.response(200, server_models.RayTaskState)
    @bp.alt_response(404, schema=error_handler.ErrorSchema)
    @bp.alt_response(500, schema=error_handler.ErrorSchema)
    def get(self, task_id):
        """
        Handle GET requests to retrieve Ray task information by task ID.
        """
        try:
            task = state.get_task(task_id)
            if task:
                return convert_ray_task_to_dict(task), 200
            else:
                return abort(404, message="Task not found")
        except ServerUnavailable as e:
            return abort(500, message=f"Error retrieving task: {str(e)}")


@bp.route('/task', endpoint='ray_tasks')
class RayTasksResource(MethodView):
    @bp.arguments(server_models.RayClusterStateFilters, location='json')
    @bp.response(200, server_models.RayTaskState(many=True))
    @bp.alt_response(404, schema=error_handler.ErrorSchema)
    @bp.alt_response(500, schema=error_handler.ErrorSchema)
    def post(self, args):
        """
        Handle POST requests to retrieve Ray task information based on filters. See https://docs.ray.io/en/latest/ray-observability/reference/doc/ray.util.state.list_tasks.html for more information.
        """
        filters = args.get('ray_cluster_filters', [])
        
        # Fetch tasks from Ray state with the provided filters
        try:
            tasks: list[TaskState] = state.list_tasks(filters=filters, detail=True, limit=constants.RAY_TASK_RETURN_LIMIT)
            if not tasks:
                return abort(404, message="No tasks found")
            task_states = [convert_ray_task_to_dict(task) for task in tasks]
            return task_states, 200
        except ServerUnavailable as e:
            return abort(500, message=f"Error retrieving tasks: {str(e)}")

@bp.route('/<annotation_class_id>/train/', endpoint='set_enable_dl')
class SetEnableDLResource(MethodView):
    @bp.arguments(server_models.SetEnableDLArgsSchema, location='query')
    @bp.response(200)
    @bp.alt_response(404, schema=error_handler.ErrorSchema)
    @bp.alt_response(408, schema=error_handler.ErrorSchema)
    @bp.alt_response(500, schema=error_handler.ErrorSchema)
    def post(self, args, annotation_class_id):
        """
        Handle POST requests to enable or disable deep learning training for a specific annotation class.
        """
        try:
            actor_name = build_actor_name(int(annotation_class_id))
            try:
                actor = ray.get_actor(actor_name)
            except ValueError:
                return abort(404, message="Actor not found")
            
            ref = actor.set_enable_training.remote(args['value'])
            try:
                ray.get(ref, timeout=10)  # wait for completion with a timeout
            except ray.exceptions.GetTimeoutError:
                return abort(408, message="Request timed out while waiting for actor response")
            
            return {}, 200
        except Exception as e:
            return abort(500, message=f"Error setting deep learning training: {str(e)}")