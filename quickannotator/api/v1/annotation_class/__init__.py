from flask_restx import Namespace, Resource
from flask import current_app, request
from sqlalchemy.sql.coercions import expect

api_ns_annotation_class = Namespace('annotation_class', description='Object class related operations')

# ------------------------ MODELS ------------------------

# ------------------------ REQUEST PARSERS ------------------------
get_annotation_class_parser = api_ns_annotation_class.parser()
get_annotation_class_parser.add_argument('annotation_class_id', location='args', type=int, required=False)
get_annotation_class_parser.add_argument('project_id', location='args', type=int, required=False)
get_annotation_class_parser.add_argument('name', location='args', type=str, required=False)



get_prediction_parser = api_ns_annotation_class.parser()
get_prediction_parser.add_argument('annotation_class_id', location='args', type=int, required=True)
get_prediction_parser.add_argument('image_id', location='args', type=int, required=True)
get_prediction_parser.add_argument('bbox_polygon', location='args', type=bytes, required=True)


# ------------------------ ROUTES ------------------------

@api_ns_annotation_class.route('/')
class AnnotationClass(Resource):
    @api_ns_annotation_class.expect(get_annotation_class_parser)
    def get(self):
        """     returns an ObjectClass      """


        return 200


    def post(self):
        """     create a new ObjectClass and instantiate a DL model    """
        return 200


    def put(self):
        """     update an existing ObjectClass      """
        return 201
    
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
@api_ns_annotation_class.route('/<int:annotation_class_id>/model/<int:image_id>/prediction')
class Prediction(Resource):
    @api_ns_annotation_class.expect(get_prediction_parser)
    def get(self, project_id, annotation_class_id):
        """     get geojson predictions for a region.     """
        return 200


