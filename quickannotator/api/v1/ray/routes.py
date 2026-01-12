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
                return abort(404)
        except ServerUnavailable as e:
            return abort(500)


@bp.route('/task', endpoint='ray_tasks')
class RayTasksResource(MethodView):
    @bp.arguments(server_models.RayClusterStateFilters, location='json')
    @bp.response(200, server_models.RayTaskState(many=True))
    @bp.alt_response(404, schema=error_handler.ErrorSchema)
    def post(self, args):
        """
        Handle POST requests to retrieve Ray task information based on filters. See https://docs.ray.io/en/latest/ray-observability/reference/doc/ray.util.state.list_tasks.html for more information.
        """
        filters = args.get('ray_cluster_filters', [])
        
        # Fetch tasks from Ray state with the provided filters
        tasks: list[TaskState] = state.list_tasks(filters=filters, detail=True, limit=constants.RAY_TASK_RETURN_LIMIT)
        if not tasks:
            return abort(404)
        task_states = [convert_ray_task_to_dict(task) for task in tasks]
        return task_states, 200

@bp.route('/train/<string:annotation_class_id>', endpoint='set_enable_dl')
class SetEnableDLResource(MethodView):
    @bp.arguments(server_models.SetEnableDLArgsSchema, location='query')
    @bp.response(200, server_models.GetDLActorStatusResponseSchema)
    @bp.alt_response(404, schema=error_handler.ErrorSchema)
    @bp.alt_response(408, schema=error_handler.ErrorSchema)
    def post(self, args, annotation_class_id):
        """
        Handle POST requests to enable or disable deep learning training for a specific annotation class.
        """
        actor_name = build_actor_name(int(annotation_class_id))
        try:
            actor = ray.get_actor(actor_name)
        except ValueError:
            return abort(404)
        
        ref = actor.set_enable_training.remote(args['enable'])
        try:
            ray.get(ref, timeout=10)  # wait for completion with a timeout
        except ray.exceptions.GetTimeoutError:
            return abort(408)
        
        # Fetch the detailed state after enabling/disabling training
        try:
            detailed_state = ray.get(actor.get_detailed_state.remote())
            return detailed_state, 200
        except Exception:
            return abort(404)

def get_actor_detailed_state(annotation_class_id):
    """
    Helper function to retrieve the detailed state of a specific actor by annotation class ID.
    """
    actor_name = build_actor_name(int(annotation_class_id))
    try:
        actor = ray.get_actor(actor_name)
    except ValueError:
        return None  # Actor does not exist

    try:
        return ray.get(actor.get_detailed_state.remote())
    except Exception:
        return None  # Error occurred while fetching the state

@bp.route('/train/status/<string:annotation_class_id>', endpoint='dl_actor_status')
class DLActorStatusResource(MethodView):
    @bp.response(200, server_models.GetDLActorStatusResponseSchema)
    @bp.alt_response(404, schema=error_handler.ErrorSchema)
    def get(self, annotation_class_id):
        """
        Handle GET requests to retrieve the current status of deep learning training for a specific annotation class.
        """
        detailed_state = get_actor_detailed_state(annotation_class_id)
        if detailed_state is None:
            return abort(404)
        return detailed_state, 200

@bp.route('/train/status', endpoint='dl_actors_status')
class DLActorsStatusResource(MethodView):
    @bp.arguments(server_models.GetDLActorsStatusArgsSchema, location='query')
    @bp.response(200, server_models.GetDLActorStatusResponseSchema(many=True))
    @bp.alt_response(404, schema=error_handler.ErrorSchema)
    def get(self, args):
        """
        Handle GET requests to retrieve the current status of deep learning training for multiple annotation classes.
        """
        annotation_class_ids = args.get('annotation_class_ids', [])
        if not annotation_class_ids:
            return abort(404)

        statuses = []
        for annotation_class_id in annotation_class_ids:
            detailed_state = get_actor_detailed_state(annotation_class_id)
            if detailed_state:
                statuses.append(detailed_state)
        return statuses, 200
