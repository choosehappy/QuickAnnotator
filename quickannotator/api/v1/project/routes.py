from flask_smorest import abort
from flask.views import MethodView
from flask import current_app
import os
import shutil
from quickannotator.db import db_session
import quickannotator.db.models as db_models
from . import models as server_models
from flask_smorest import Blueprint
from datetime import datetime
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.image import get_images_by_project_id
from quickannotator.api.v1.image.utils import delete_annotation_tables_by_image_id
import sqlalchemy
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
    def delete(self, args):
        """     delete a Project
        """
        project_id = args['project_id']
    
        # get all image ids by project id
        images = get_images_by_project_id(project_id)
        # delete all annotation tables
        for img in images:
            delete_annotation_tables_by_image_id(image_id=img.id)
        
        # delete images
        db_session.query(db_models.Image).filter(db_models.Image.project_id == project_id).delete()
        # delete project
        db_session.query(db_models.Project).filter(db_models.Project.id == project_id).delete()

        db_session.commit()

        # remove the project folders
        projects_path = 'mounts/nas_write/projects'
        full_project_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}')
        if os.path.exists(full_project_path):
            try:
                shutil.rmtree(full_project_path)
            except OSError as e:
                print(f"Error deleting folder '{full_project_path}': {e}")
                
        
        # return response
        if project_id:
            return {'project_id': project_id}, 204
        else:
            return {"message": "Project not found"}, 404

@bp.route('/all')
class SearchProject(MethodView):
    """     get all Projects

    """
    @bp.arguments(server_models.SearchProjectArgsSchema, location='query')
    @bp.response(200, server_models.ProjectRespSchema(many=True))
    def get(self, args):
        projects = db_session.query(db_models.Project).all()
        return projects