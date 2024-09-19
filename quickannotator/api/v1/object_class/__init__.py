from flask_restx import Namespace, Resource
from flask import current_app, request

api_ns_object_class = Namespace('object_class', description='Object class related operations')

@api_ns_object_class.route('/<string:project_id>')
class ObjectClass(Resource):
    @api_ns_object_class.doc(params={'project_id': 'Which project?', 'object_class_id': 'Which object class?'})
    def get(self, project_id):
        """     returns an """