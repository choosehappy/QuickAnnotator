from quickannotator.db.crud.annotation import get_annotation_count
from quickannotator.db.crud.image import get_images_by_project_id
from quickannotator.db.crud.annotation_class import get_all_annotation_classes_for_project, get_annotation_class_by_id
from flask_smorest import abort
from flask.views import MethodView
from quickannotator.api.v1.project.utils import delete_project_and_related_data
from quickannotator.db import db_session
from quickannotator.db.crud.project import get_project_by_id
import quickannotator.db.models as db_models
from . import models as server_models
from flask_smorest import Blueprint
from datetime import datetime
from flask import request

# Import DB helpers for stats (implement or update as needed)
from quickannotator.db import crud
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


# --- New Project Stats Endpoints ---

@bp.route('/<int:project_id>/annotations/stats/')
class ProjectAnnotationStats(MethodView):
    @bp.arguments(server_models.ProjectAnnotationStatsArgsSchema, location='query')
    @bp.response(200, server_models.AnnotationStatRespSchema(many=True))
    def get(self, args, project_id):
        """
        Returns annotation stats grouped by annotation_class or image.
        """
        group_by = args.get('group_by', 'annotation_class')
        annotation_class_ids = args.get('annotation_class_ids')
        image_ids = args.get('image_ids')

        if annotation_class_ids:
            annotation_class_ids = [int(x) for x in annotation_class_ids.split(',') if x.strip()]
        else:
            annotation_class_ids = None
        if image_ids:
            image_ids = [int(x) for x in image_ids.split(',') if x.strip()]
        else:
            image_ids = None

        images = get_images_by_project_id(project_id)
        annotation_classes = get_all_annotation_classes_for_project(project_id)

        if image_ids is not None:
            images = [img for img in images if img.id in image_ids]
        if annotation_class_ids is not None:
            annotation_classes = [ac for ac in annotation_classes if ac.id in annotation_class_ids]

        result = []
        if group_by == 'annotation_class':
            for ann_cls in annotation_classes:
                count = sum(get_annotation_count(img.id, ann_cls.id, is_gt=True) for img in images)
                result.append({
                    "group_id": ann_cls.id,
                    "group_label": ann_cls.name,
                    "stats": {"count": count}
                })
        elif group_by == 'image':
            for img in images:
                count = sum(get_annotation_count(img.id, ann_cls.id, is_gt=True) for ann_cls in annotation_classes)
                result.append({
                    "group_id": img.id,
                    "group_label": getattr(img, 'name', str(img.id)),
                    "stats": {"count": count}
                })
        else:
            abort(400, "Invalid group_by value. Must be 'annotation_class' or 'image'.")

        return result


@bp.route('/<int:project_id>/annotation_class/stats')
class ProjectAnnotationClassStats(MethodView):
    @bp.response(200, server_models.ProjectCountRespSchema)
    def get(self, project_id):
        """Returns annotation class count for the project."""
        count = len(get_all_annotation_classes_for_project(project_id))
        return {"stats": {"count": count}}


@bp.route('/<int:project_id>/image/stats')
class ProjectImageStats(MethodView):
    @bp.response(200, server_models.ProjectCountRespSchema)
    def get(self, project_id):
        """Returns image count for the project."""
        count = len(get_images_by_project_id(project_id))
        return {"stats": {"count": count}}