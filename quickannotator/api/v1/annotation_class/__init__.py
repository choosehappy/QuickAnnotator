from flask_restx import Namespace, Resource
from flask import current_app, request

api_ns_annotation_class = Namespace('annotation_class', description='Object class related operations')

# ------------------------ MODELS ------------------------

# ------------------------ REQUEST PARSERS ------------------------

# ------------------------ ROUTES ------------------------

@api_ns_annotation_class.route('/<int:project_id>')
class AnnotationClass(Resource):
    @api_ns_annotation_class.doc(params={'project_id': 'Which project?', 'annotation_class_id': 'Which object class?'})
    def get(self, project_id):
        """     returns an ObjectClass      """
        return 200

    @api_ns_annotation_class.doc(params={'project_id': 'Which project?'})
    def post(self, project_id):
        """     create a new ObjectClass and instantiate a DL model    """
        return 200

    @api_ns_annotation_class.doc(params={'project_id': 'Which project?', 'annotation_class_id': 'Which object class?'})
    def put(self, project_id):
        """     update an existing ObjectClass      """
        return 201
    
    def delete(self, project_id):
        """     delete an ObjectClass      """
        return 204

####################################################################################################
@api_ns_annotation_class.route('/<int:project_id>/<int:annotation_class_id>/model')
class DLModel(Resource):
    @api_ns_annotation_class.doc(params={'project_id': 'Which project?', 'annotation_class_id': 'Which object class?'})
    def get(self, project_id, annotation_class_id):
        """     get the state of the DL model service     """
        return 200

    @api_ns_annotation_class.doc(params={'project_id': 'Which project?', 'annotation_class_id': 'Which object class?'})
    def post(self, project_id, annotation_class_id):
        """     instantiate a new DL model or update the state     """
        return 200

####################################################################################################
@api_ns_annotation_class.route('/<int:project_id>/<int:annotation_class_id>/model/<int:image_id>/prediction')
class Prediction(Resource):
    @api_ns_annotation_class.doc(params={'project_id': 'Which project?', 'annotation_class_id': 'Which object class?', 'image_id': 'Which image?'})
    def get(self, project_id, annotation_class_id):
        """     get geojson predictions for a region.     """
        return 200


