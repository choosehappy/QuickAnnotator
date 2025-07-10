from flask_smorest import abort
from flask.views import MethodView
from quickannotator.api.v1.project.utils import delete_project_and_related_data
from quickannotator.db import db_session
from quickannotator.db.crud.project import get_project_by_id
import quickannotator.db.models as db_models
from . import models as server_models
from flask_smorest import Blueprint
from datetime import datetime
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
            abort(404, "Project not found")

    @bp.arguments(server_models.PostProjectArgsSchema, location='json')
    @bp.response(200, server_models.ProjectRespSchema, description="Project created")
    def post(self, args):
        """     create a new Project
        """
        # create a new project
        new_project = db_models.Project(name=args['name'], description=args['description'], is_dataset_large=args['is_dataset_large'])
        db_session.add(new_project)
        db_session.commit()
        return  new_project

    @bp.arguments(server_models.PutProjectArgsSchema, location='json')
    @bp.response(200, server_models.ProjectRespSchema, description="Project updated")
    def put(self, args):
        """     update a Project

        """
        id = args['project_id']        
        name = args['name']
        description = args['description']
        is_dataset_large = args['is_dataset_large']
        project = db_session.query(db_models.Project).filter(db_models.Project.id == id).first()

        if project:
            project.name = name
            project.is_dataset_large = is_dataset_large
            project.description = description
            project.datetime = datetime.now()
            db_session.commit()
        
        return project
    
    
    @bp.arguments(server_models.DeleteProjectArgsSchema, location='query')
    @bp.response(204, description="Project deleted")
    @bp.response(404, description="Project not found")
    def delete(self, args):
        """     delete a Project
        """
        project_id = args['project_id']

        # Check that the project exists
        project = get_project_by_id(project_id)

        if project is None:
            abort(404, "Project not found")
            
        delete_project_and_related_data(project_id)

        return {}, 204

@bp.route('/all')
class SearchProject(MethodView):
    """     get all Projects

    """
    @bp.arguments(server_models.SearchProjectArgsSchema, location='query')
    @bp.response(200, server_models.ProjectRespSchema(many=True))
    def get(self, args):
        projects = db_session.query(db_models.Project).all()
        return projects