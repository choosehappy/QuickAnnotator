import logging
from quickannotator import constants
from quickannotator.api.v1.annotation_class.utils import delete_annotation_class_and_related_data
from quickannotator.db.colors import ColorPalette
from . import models as server_models
from flask import abort
import quickannotator.db.models as db_models
from quickannotator.db import db_session
from quickannotator.db.crud.annotation_class import get_all_annotation_classes, get_all_annotation_classes_for_project, get_annotation_class_by_id, get_annotation_class_by_name, insert_annotation_class, put_annotation_class
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
            abort(404, "AnnotationClass not found")


    @bp.arguments(server_models.PostAnnClassArgsSchema, location='query')
    @bp.response(201, server_models.AnnClassRespSchema, description="AnnotationClass created")
    def post(self, args):
        """     create a new AnnotationClass   """

        annotation_class = db_models.AnnotationClass(project_id=args['project_id'],
                                          name=args['name'],
                                          color=args['color'],
                                          work_mag=args['work_mag'],
                                          work_tilesize=args['tile_size']
                                          )
        db_session.add(annotation_class)
        db_session.commit()  # Ensure the object is synced with the database
        return annotation_class, 201


    @bp.arguments(server_models.PutAnnClassArgsSchema, location='query')
    @bp.response(201, server_models.AnnClassRespSchema, description="AnnotationClass updated")
    def put(self, args):
        """     update an existing AnnotationClass      """
        annotation_class = put_annotation_class(args['annotation_class_id'],
                             name=args['name'],
                             color=args['color'])
        return annotation_class, 201

    @bp.arguments(server_models.GetAnnClassArgsSchema, location='query')
    @bp.response(204, server_models.AnnClassRespSchema, description="AnnotationClass deleted")
    def delete(self, args):
        """     delete an AnnotationClass      """

        # Check that the annotation class id is not the mask class id
        if args['annotation_class_id'] == constants.MASK_CLASS_ID:
            abort(400, "Cannot delete the mask annotation class")

        # Check that the annotation class exists
        annotation_class = get_annotation_class_by_id(args['annotation_class_id'])
        if annotation_class is None:
            abort(404, "AnnotationClass not found")
        
        delete_annotation_class_and_related_data(args['annotation_class_id'])
        return {}, 204

####################################################################################################

@bp.route('/search')
class SearchAnnotationClass(MethodView):
    @bp.arguments(server_models.SearchAnnClassArgsSchema, location='query')
    @bp.response(200, server_models.AnnClassRespSchema(many=True))
    def get(self, args):
        """     search for an AnnotationClass by name or project_id     """
        if 'name' in args and 'project_id' in args:
            result = [get_annotation_class_by_name(args['project_id'], args['name'])]
        elif 'project_id' in args:
            result = [get_annotation_class_by_id(constants.MASK_CLASS_ID)]  # Always include the mask class
            result.extend(get_all_annotation_classes_for_project(args['project_id']))
        else:
            result = get_all_annotation_classes()

        return result, 200

####################################################################################################
@bp.route('/<int:annotation_class_id>/startproc')
class DLActor(MethodView):
    @bp.response(200, description="DLActor created")
    def post(self, annotation_class_id):
        """     trigger the DLActor for the current annotation class to start processing    """
        actor = start_processing(annotation_class_id)

        if actor is None:
            abort(404, description="Failed to create DL Actor")
        else:
            return {}, 200

####################################################################################################

@bp.route('/color/<int:project_id>')
class NewColor(MethodView):
    @bp.response(200, description="New color generated")
    def get(self, project_id):
        """     generate a new color for the current project     """
        try:
            color_palette = ColorPalette(project_id)
            new_color = color_palette.get_unused_color()
            return {'color': new_color}, 200
        except ValueError as e:
            abort(400, str(e))
        except KeyError as e:
            abort(400, str(e))

@bp.route('/magnifications')
class Magnifications(MethodView):
    @bp.response(200, description="Available magnifications")
    def get(self):
        """     get the available magnifications     """
        return {'magnifications': constants.MAGNIFICATION_OPTIONS}, 200
    
@bp.route('/tilesizes')
class Tilesizes(MethodView):
    @bp.response(200, description="Available tilesizes")
    def get(self):
        """     get the available tilesizes     """
        return {'tilesizes': constants.TILESIZE_OPTIONS}, 200