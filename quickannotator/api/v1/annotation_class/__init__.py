from flask_smorest import Blueprint, abort
from marshmallow import fields, Schema
from flask.views import MethodView
import quickannotator.db.models as models
from quickannotator.db import db_session
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from quickannotator.db.annotation_class_crud import get_annotation_class_by_id
from quickannotator.dl.ray_jackson import start_processing


bp = Blueprint('annotation_class', __name__, description='AnnotationClass operations')

# ------------------------ RESPONSE MODELS ------------------------
class AnnClassRespSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.AnnotationClass


class GetAnnClassArgsSchema(Schema):
    annotation_class_id = fields.Int(required=True)

class PostAnnClassArgsSchema(Schema):
    project_id = fields.Int(required=True)
    name = fields.Str(required=True)
    color = fields.Str(required=True)
    work_mag = fields.Int(required=True)

class PutAnnClassArgsSchema(Schema):
    name = fields.Str(required=False)
    color = fields.Str(required=False)

class SearchAnnClassArgsSchema(Schema):
    name = fields.Str(required=False)
    project_id = fields.Int(required=False)


# ------------------------ ROUTES ------------------------

@bp.route('/')
class AnnotationClass(MethodView):
    @bp.arguments(GetAnnClassArgsSchema, location='query')
    @bp.response(200, AnnClassRespSchema)
    def get(self, args):
        """     returns an AnnotationClass      """

        result = get_annotation_class_by_id(args['annotation_class_id'])
        if result is not None:
            return result, 200
        else:
            abort(404, message="AnnotationClass not found")


    @bp.arguments(PostAnnClassArgsSchema, location='query')
    @bp.response(200, description="AnnotationClass created")
    def post(self, args):
        """     create a new AnnotationClass   """

        annotation_class = models.AnnotationClass(project_id=args['project_id'],
                                          name=args['name'],
                                          color=args['color'],
                                          work_mag=args['work_mag'],
                                          work_tilesize=2048
                                          )
        db_session.add(annotation_class)
        return {'annotation_class_id':annotation_class.id}, 200


    @bp.arguments(PutAnnClassArgsSchema, location='query')
    @bp.response(201, description="AnnotationClass updated")
    def put(self, args):
        """     update an existing AnnotationClass      """
        return 201

    @bp.arguments(GetAnnClassArgsSchema, location='query')
    @bp.response(204, description="AnnotationClass deleted")
    def delete(self, args):
        """     delete an ObjectClass      """
        return db_session.query(models.AnnotationClass).filter(models.AnnotationClass.id == args['annotation_class_id']).delete(), 204

####################################################################################################

@bp.route('/search')
class SearchAnnotationClass(MethodView):
    @bp.arguments(SearchAnnClassArgsSchema, location='query')
    @bp.response(200, AnnClassRespSchema(many=True))
    def get(self, args):
        """     search for an AnnotationClass by name or project_id     """
        if 'name' in args:
            result = db_session.query(models.AnnotationClass).filter(models.AnnotationClass.name == args['name']).all()
        elif 'project_id' in args:
            result = db_session.query(models.AnnotationClass).filter(models.AnnotationClass.project_id == args['project_id']).all()
        else:
            result = db_session.query(models.AnnotationClass).all()
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