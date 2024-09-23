from flask_restx import Namespace, Resource
from flask import current_app, request

api_ns_object_class = Namespace('object_class', description='Object class related operations')

@api_ns_object_class.route('/<string:project_id>')
class ObjectClass(Resource):
    @api_ns_object_class.doc(params={'project_id': 'Which project?', 'object_class_id': 'Which object class?'})
    def get(self, project_id):
        """     returns an ObjectClass      """
        return 200

    @api_ns_object_class.doc(params={'project_id': 'Which project?'})
    def post(self, project_id):
        """     create a new ObjectClass and instantiate a DL model    """
        return 200

    @api_ns_object_class.doc(params={'project_id': 'Which project?', 'object_class_id': 'Which object class?'})
    def put(self, project_id):
        """     update an existing ObjectClass      """
        return 201


@api_ns_object_class.route('/<string:project_id>/<string:object_class_id>/model')
class DLModel(Resource):
    @api_ns_object_class.doc(params={'project_id': 'Which project?', 'object_class_id': 'Which object class?'})
    def get(self, project_id, object_class_id):
        """     get the state of the DL model service     """
        return 200

    @api_ns_object_class.doc(params={'project_id': 'Which project?', 'object_class_id': 'Which object class?'})
    def post(self, project_id, object_class_id):
        """     instantiate a new DL model or update the state     """
        return 200

@api_ns_object_class.route('/<string:project_id>/<string:object_class_id>/model/<string:image_id>/prediction')
class Prediction(Resource):
    @api_ns_object_class.doc(params={'project_id': 'Which project?', 'object_class_id': 'Which object class?', 'image_id': 'Which image?'})
    def get(self, project_id, object_class_id):
        """     get geojson predictions for a region.     """
        return 200

