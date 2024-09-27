from flask_restx import Namespace, Resource
from sqlalchemy.sql.coercions import expect

api_ns_annotation = Namespace('annotation', description='Annotation related operations')

# ------------------------ MODELS ------------------------

# ------------------------ REQUEST PARSERS ------------------------
## GET Annotation parser
get_annotation_parser = api_ns_annotation.parser()
get_annotation_parser.add_argument('project_id', location='args', type=int, required=True)
get_annotation_parser.add_argument('image_id', location='args', type=int, required=True)
get_annotation_parser.add_argument('annotation_class_id', location='args', type=int, required=True)
get_annotation_parser.add_argument('gt_or_pred', location='args', type=str, required=True, choices=['gt', 'pred'])
get_annotation_parser.add_argument('annotation_id', location='args', type=int, required=False)
get_annotation_parser.add_argument('upper_left_coord', location='args', type=bytes, required=False)

## POST Annotation parser
post_annotation_parser = api_ns_annotation.parser()
post_annotation_parser.add_argument('project_id', location='args', type=int, required=True)
post_annotation_parser.add_argument('image_id', location='args', type=int, required=True)
post_annotation_parser.add_argument('annotation_class_id', location='args', type=int, required=True)
post_annotation_parser.add_argument('gt_or_pred', location='args', type=str, required=True, choices=['gt', 'pred'])
post_annotation_parser.add_argument('polygon', location='args', type=bytes, required=True)

## PUT Annotation parser
put_annotation_parser = api_ns_annotation.parser()
put_annotation_parser.add_argument('project_id', location='args', type=int, required=True)
put_annotation_parser.add_argument('image_id', location='args', type=int, required=True)
put_annotation_parser.add_argument('annotation_class_id', location='args', type=int, required=True)
put_annotation_parser.add_argument('gt_or_pred', location='args', type=str, required=True, choices=['gt', 'pred'])
put_annotation_parser.add_argument('annotation_id', location='args', type=int, required=False)
put_annotation_parser.add_argument('centroid', location='args', type=bytes, required=False)
put_annotation_parser.add_argument('area', location='args', type=str, required=False)
put_annotation_parser.add_argument('polygon', location='args', type=bytes, required=False)
put_annotation_parser.add_argument('custom_metrics', location='args', type=dict, required=False)

## DELETE Annotation parser
delete_annotation_parser = api_ns_annotation.parser()
delete_annotation_parser.add_argument('annotation_id', location='args', type=int, required=True)
# ------------------------ ROUTES ------------------------

@api_ns_annotation.route('/')
class Annotation(Resource):
    @api_ns_annotation.expect(get_annotation_parser)
    def get(self):
        """     returns an Annotation or list of Annotations
        # Implementation details
        1. If annotation_id is provided, return the annotation with that id
        2. If annotation_id is not provided, return annotations within the bounding box
        """

        return 200

    @api_ns_annotation.expect(post_annotation_parser)
    def post(self):
        """     create a new annotation

        """

        return 200

    @api_ns_annotation.expect(put_annotation_parser)
    def put(self):
        """     create or update an annotation directly in the database

        """

        return 201

    @api_ns_annotation.expect(delete_annotation_parser)
    def delete(self):
        """     delete an annotation

        """

        return 204
