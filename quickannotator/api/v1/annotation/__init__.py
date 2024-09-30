from flask_restx import Namespace, Resource

api_ns_annotation = Namespace('annotation', description='Annotation related operations')

# ------------------------ MODELS ------------------------

# ------------------------ REQUEST PARSERS ------------------------
base_parser = api_ns_annotation.parser()
base_parser.add_argument('project_id', location='args', type=int)
base_parser.add_argument('image_id', location='args', type=int)
base_parser.add_argument('gt_or_pred', location='args', type=str, choices=['gt', 'pred'])
base_parser.add_argument('annotation_class_id', location='args', type=int)


## GET Annotation parser
get_annotation_parser = base_parser.copy()
get_annotation_parser.add_argument('annotation_id', location='args', type=int, required=False)

## GET Annotation search parser
get_annotation_search_parser = base_parser.copy()
get_annotation_search_parser.add_argument('bbox_polygon', location='args', type=bytes, required=False)

## POST Annotation parser
post_annotation_parser = base_parser.copy()
post_annotation_parser.add_argument('polygon', location='args', type=bytes, required=True)

## PUT Annotation parser
put_annotation_parser = base_parser.copy()
put_annotation_parser.add_argument('annotation_id', location='args', type=int, required=False)
put_annotation_parser.add_argument('centroid', location='args', type=bytes, required=False)
put_annotation_parser.add_argument('area', location='args', type=str, required=False)
put_annotation_parser.add_argument('polygon', location='args', type=bytes, required=False)
put_annotation_parser.add_argument('custom_metrics', location='args', type=dict, required=False)

## DELETE Annotation parser
delete_annotation_parser = base_parser.copy()
delete_annotation_parser.add_argument('annotation_id', location='args', type=int, required=True)

## POST Annotation Dry Run parser
post_dryrun_parser = post_annotation_parser.copy()
post_dryrun_parser.remove_argument('image_id')


# ------------------------ ROUTES ------------------------

@api_ns_annotation.route('/<int:project_id>/<int:image_id>/<string:gt_or_pred>/<int:annotation_class_id>')
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

@api_ns_annotation.route('/search')
class AnnotationSearch(Resource):
    @api_ns_annotation.expect(get_annotation_search_parser)
    def get(self):
        """     search for annotations

        """

        return 200

@api_ns_annotation.route('/dryrun')
class AnnotationDryRun(Resource):
    @api_ns_annotation.expect(post_dryrun_parser)
    def post(self):
        """     perform a dry run for the given annotation

        """

        return 200