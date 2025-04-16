from flask_smorest import abort
from flask.views import MethodView
from quickannotator.db import db_session
import quickannotator.db.models as db_models
from . import models as server_models
from flask_smorest import Blueprint

bp = Blueprint('project', __name__, description='Project operations')

@bp.route('/')
class Project(MethodView):
    @bp.arguments(server_models.GetProjectArgsSchema, location='query')
    @bp.response(200, server_models.ProjectRespSchema)
    def get(self, args):
        """     returns a Project
        """
        project_id = args['project_id']
        project = db_session.query(db_models.Project).filter(db_models.Project.id == project_id).first()
        if project is not None:
            return project
        else:
            abort(404, message="Project not found")

    @bp.arguments(server_models.PostProjectArgsSchema, location='json')
    @bp.response(200, description="Project created")
    def post(self, args):
        """     create a new Project
        """

        db_session.add(db_models.Project(name=args['name'], description=args['description'], is_dataset_large=args['is_dataset_large']))
        return 200


    @bp.arguments(server_models.PutProjectArgsSchema, location='json')
    @bp.response(201, description="Project updated")
    def put(self, args):
        """     update a Project

        """

        return 201

    @bp.arguments(server_models.DeleteProjectArgsSchema, location='query')
    @bp.response(204, description="Project deleted")
    def delete(self, args):
        """     delete a Project

        """

        return 204

@bp.route('/all')
class SearchProject(MethodView):
    """     get all Projects

    """
    @bp.arguments(server_models.SearchProjectArgsSchema, location='query')
    @bp.response(200, server_models.ProjectRespSchema(many=True))
    def get(self, args):
        result = db_session.query(db_models.Project).all()
        return result