from flask_restx import Namespace, Resource, fields
from flask import current_app, request
from sqlalchemy.sql.coercions import expect

api_ns_annotation_class = Namespace('annotation_class', description='Object class related operations')

# ------------------------ RESPONSE MODELS ------------------------
annotation_class_model = api_ns_annotation_class.model("AnnotationClass", {
    'id': fields.Integer(),
    'name': fields.String(),
    'color': fields.String(),
    'magnification': fields.Integer(description='DL model parameter for working magnification.'),
    'patchsize': fields.Integer(description='DL model parameter for working patchsize.'),
    'tilesize': fields.Integer(description='DL model parameter for tilesize. Will be a multiple of the patchsize.'),
    'date': fields.DateTime(description='The date of class creation.')
})
# ------------------------ REQUEST PARSERS ------------------------
get_annotation_class_parser = api_ns_annotation_class.parser()
get_annotation_class_parser.add_argument('annotation_class_id', location='args', type=int, required=False)
get_annotation_class_parser.add_argument('project_id', location='args', type=int, required=False)
get_annotation_class_parser.add_argument('name', location='args', type=str, required=False)

# ------------------------ ROUTES ------------------------

@api_ns_annotation_class.route('/')
class AnnotationClass(Resource):
    @api_ns_annotation_class.expect(get_annotation_class_parser)
    @api_ns_annotation_class.marshal_with(annotation_class_model)
    def get(self):
        """     returns an AnnotationClass      """


        return {}, 200


    def post(self):
        """     create a new ObjectClass and instantiate a DL model    """
        return 200

    @api_ns_annotation_class.response(201, "AnnotationClass  created/updated")
    def put(self):
        """     update an existing ObjectClass      """
        return 201

    @api_ns_annotation_class.response(201, "AnnotationClass  deleted")
    def delete(self):
        """     delete an ObjectClass      """
        return 204

####################################################################################################
@api_ns_annotation_class.route('/<int:annotation_class_id>/model')
class DLModel(Resource):
    def get(self, annotation_class_id):
        """     get the state of the DL model service     """
        return 200

    def post(self, annotation_class_id):
        """     instantiate a new DL model or update the state     """
        return 200

####################################################################################################