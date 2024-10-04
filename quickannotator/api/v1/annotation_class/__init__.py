from flask_smorest import Blueprint, abort
from marshmallow import fields, Schema
from flask.views import MethodView
import quickannotator.db as qadb
from quickannotator.db import db

bp = Blueprint('annotation_class', __name__, description='AnnotationClass operations')

# ------------------------ RESPONSE MODELS ------------------------
class AnnClassRespSchema(Schema):
    """     AnnotationClass response schema      """
    id = fields.Int()
    name = fields.Str()
    color = fields.Str()
    magnification = fields.Int()
    patchsize = fields.Int()
    tilesize = fields.Int()
    dl_model_objectref = fields.Str()
    datetime = fields.DateTime()

class GetAnnClassArgsSchema(Schema):
    annotation_class_id = fields.Int(required=True)

class PostAnnClassArgsSchema(Schema):
    proj_id = fields.Int(required=True)
    name = fields.Str(required=True)
    color = fields.Str(required=True)
    magnification = fields.Int(required=True)

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

        result = db.session.query(qadb.AnnotationClass).filter(qadb.AnnotationClass.id == args['annotation_class_id']).first()
        if result is not None:
            return result, 200
        else:
            abort(404, message="AnnotationClass not found")


    @bp.arguments(PostAnnClassArgsSchema, location='query')
    @bp.response(200, description="AnnotationClass created")
    def post(self, args):
        """     create a new AnnotationClass and instantiate a DL model    """

        annotation = qadb.AnnotationClass(proj_id=args['proj_id'],
                                          name=args['name'],
                                          color=args['color'],
                                          magnification=args['magnification'],
                                          patchsize=256,
                                          tilesize=2048,
                                          dl_model_objectref=None
                                          )
        db.session.add(annotation)
        db.session.commit()
        return {'annotation_class_id':annotation.id}, 200


    @bp.arguments(PutAnnClassArgsSchema, location='json')
    @bp.response(201, description="AnnotationClass updated")
    def put(self, args):
        """     update an existing ObjectClass      """
        return 201

    @bp.arguments(GetAnnClassArgsSchema, location='query')
    @bp.response(204, description="AnnotationClass deleted")
    def delete(self, args):
        """     delete an ObjectClass      """
        return db.session.query(qadb.AnnotationClass).filter(qadb.AnnotationClass.id == args['annotation_class_id']).delete(), 204

####################################################################################################

@bp.route('/search')
class SearchAnnotationClass(MethodView):
    @bp.arguments(SearchAnnClassArgsSchema, location='query')
    @bp.response(200, AnnClassRespSchema(many=True))
    def get(self, args):
        """     search for an AnnotationClass by name or project_id     """
        if 'name' in args:
            result = db.session.query(qadb.AnnotationClass).filter(qadb.AnnotationClass.name == args['name']).all()
        elif 'project_id' in args:
            result = db.session.query(qadb.AnnotationClass).filter(qadb.AnnotationClass.proj_id == args['project_id']).all()
        else:
            result = db.session.query(qadb.AnnotationClass).all()
        return result, 200

####################################################################################################
@bp.route('/<int:annotation_class_id>/model')
class DLModel(MethodView):
    def get(self, annotation_class_id):
        """     get the state of the DL model service     """
        return 200

    def post(self, annotation_class_id):
        """     instantiate a new DL model or update the state     """
        return 200

####################################################################################################