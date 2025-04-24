from . import models as server_models
from flask import abort
import quickannotator.db.models as db_models
from quickannotator.db import db_session
from quickannotator.db.crud.annotation_class import get_annotation_class_by_id, insert_annotation_class, put_annotation_class
from quickannotator.dl.ray_jackson import start_processing

from flask.views import MethodView
from flask_smorest import Blueprint

bp = Blueprint('annotation_class', __name__, description='AnnotationClass operations')


@bp.route('/')
class AnnotationClass(MethodView):
    @bp.arguments(server_models.GetAnnClassArgsSchema, location='query')
    @bp.response(200, server_models.AnnClassRespSchema)
    def get(self, args):
        """     returns an AnnotationClass      """

        result = get_annotation_class_by_id(args['annotation_class_id'])
        if result is not None:
            return result, 200
        else:
            abort(404, message="AnnotationClass not found")


    @bp.arguments(server_models.PostAnnClassArgsSchema, location='query')
    @bp.response(200, description="AnnotationClass created")
    def post(self, args):
        """     create a new AnnotationClass   """

        annotation_class = insert_annotation_class(
            project_id=args['project_id'],
            name=args['name'],
            color=args['color'],
            work_mag=args['work_mag'],
            work_tilesize=2048)
        
        return {'annotation_class_id':annotation_class.id}, 200


    @bp.arguments(server_models.PutAnnClassArgsSchema, location='query')
    @bp.response(201, server_models.AnnClassRespSchema, description="AnnotationClass updated")
    def put(self, args):
        """     update an existing AnnotationClass      """
        annotation_class = put_annotation_class(args['annotation_class_id'],
                             name=args['name'],
                             color=args['color'])
        return annotation_class, 201

    @bp.arguments(server_models.GetAnnClassArgsSchema, location='query')
    @bp.response(204, description="AnnotationClass deleted")
    def delete(self, args):
        """     delete an ObjectClass      """
        return db_session.query(db_models.AnnotationClass).filter(db_models.AnnotationClass.id == args['annotation_class_id']).delete(), 204

####################################################################################################

@bp.route('/search')
class SearchAnnotationClass(MethodView):
    @bp.arguments(server_models.SearchAnnClassArgsSchema, location='query')
    @bp.response(200, server_models.AnnClassRespSchema(many=True))
    def get(self, args):
        """     search for an AnnotationClass by name or project_id     """
        if 'name' in args:
            result = db_session.query(db_models.AnnotationClass).filter(db_models.AnnotationClass.name == args['name']).all()
        elif 'project_id' in args:
            result = db_session.query(db_models.AnnotationClass).filter(db_models.AnnotationClass.project_id == args['project_id']).all()
        else:
            result = db_session.query(db_models.AnnotationClass).all()
        return result, 200

####################################################################################################
@bp.route('/<int:annotation_class_id>/startproc')
class DLActor(MethodView):
    @bp.response(200, description="DLActor created")
    def post(self, annotation_class_id):
        """     trigger the DLActor for the current annotation class to start processing    """
        actor = start_processing(annotation_class_id)

        if actor is None:
            abort(404, message="Failed to create DL Actor")
        else:
            return {}, 200

####################################################################################################