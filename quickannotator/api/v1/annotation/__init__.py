from flask_restx import Namespace, Resource, fields

api_ns_annotation = Namespace('annotation', description='Annotation related operations')

# ------------------------ MODELS ------------------------
annotation_model = api_ns_annotation.model('Annotation', {
    'id': fields.Integer(description='Annotation ID'),
    'centroid': fields.String(description="the annotation centroid in WKB"),
    'area': fields.Float(description="the annotation area"),
    'polygon': fields.String(description="the annotation polygon in WKB"),
    'custom_metrics': fields.Raw(description="the annotation custom metrics"),
    'date': fields.DateTime(description="the date of last modification")
})

# ------------------------ REQUEST PARSERS ------------------------
base_parser = api_ns_annotation.parser()
base_parser.add_argument('is_gt', location='args', type=bool, required=True)

## GET Annotation parser
get_annotation_parser = base_parser.copy()
get_annotation_parser.add_argument('annotation_id', location='args', type=int, required=True)

## GET Annotation search parser
get_annotation_search_parser = base_parser.copy()
get_annotation_search_parser.add_argument('bbox_polygon', location='args', type=bytes, required=False)

## POST Annotation parser
post_annotation_parser = base_parser.copy()
post_annotation_parser.add_argument('polygon', location='args', type=bytes, required=True)

## PUT Annotation parser
put_annotation_parser = base_parser.copy()
put_annotation_parser.add_argument('centroid', location='args', type=bytes, required=False)
put_annotation_parser.add_argument('area', location='args', type=str, required=False)
put_annotation_parser.add_argument('polygon', location='args', type=bytes, required=False)
put_annotation_parser.add_argument('custom_metrics', location='args', type=dict, required=False)

## DELETE Annotation parser
delete_annotation_parser = get_annotation_parser.copy()

## POST Annotation Dry Run parser
post_dryrun_parser = post_annotation_parser.copy()
post_dryrun_parser.add_argument('script', location='args', type=str, required=True)


# ------------------------ ROUTES ------------------------

@api_ns_annotation.route('/<int:image_id>/<int:annotation_class_id>')
class Annotation(Resource):
    @api_ns_annotation.expect(get_annotation_parser)
    @api_ns_annotation.marshal_with(annotation_model)
    def get(self):
        """     returns an Annotation
        """

        return 200

    @api_ns_annotation.expect(post_annotation_parser)
    def post(self):
        """     process a new annotation

        """

        return 200

    @api_ns_annotation.expect(put_annotation_parser)
    @api_ns_annotation.response(201, "Annotation  created/updated")
    def put(self):
        """     create or update an annotation directly in the database

        """

        return 201

    @api_ns_annotation.expect(delete_annotation_parser)
    @api_ns_annotation.response(204, "Annotation  deleted")
    def delete(self):
        """     delete an annotation

        """

        return {}, 204

#################################################################################
@api_ns_annotation.route('/<int:image_id>/<int:annotation_class_id>/search')
class SearchAnnotations(Resource):
    @api_ns_annotation.expect(get_annotation_search_parser)
    @api_ns_annotation.marshal_with(annotation_model, as_list=True)
    def get(self):
        """     search for annotations
            # Implementation
            # Questions
            1. What is the appropriate response format? A list of Annotations (each includes a geojson polygon), or a pure geojson response?
        """

        return 200

#################################################################################
@api_ns_annotation.route('/<int:image_id>/<int:annotation_class_id>/predict')
class PredictAnnotations(Resource):
    """     request new DL model predictions
    """
    @api_ns_annotation.expect(get_annotation_search_parser)
    @api_ns_annotation.marshal_with(annotation_model, as_list=True)
    def post(self, image_id, annotation_class_id):
        return {}, 200

#################################################################################
@api_ns_annotation.route('/<int:annotation_class>/dryrun')
class AnnotationDryRun(Resource):
    @api_ns_annotation.expect(post_dryrun_parser)
    def post(self):
        """     perform a dry run for the given annotation

        """

        return 200

