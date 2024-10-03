from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView

bp = Blueprint('annotation', __name__, description='Annotation operations')


# ------------------------ MODELS ------------------------
class AnnRespSchema(Schema):
    """     Annotation response schema      """
    id = fields.Int()
    centroid = fields.String()
    area = fields.Float()
    polygon = fields.String()
    custom_metrics = fields.Raw()
    datetime = fields.DateTime()

class GetAnnArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    annotation_id = fields.Int()

class GetAnnSearchArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    bbox_polygon = fields.String(required=True)

class PostAnnArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    polygon = fields.String(required=True)

class PutAnnArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    annotation_id = fields.Int()
    centroid = fields.String()
    area = fields.Str()
    polygon = fields.String()
    custom_metrics = fields.Dict()

class DeleteAnnArgsSchema(GetAnnArgsSchema):
    pass

class PostDryRunArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    polygon = fields.String(required=True)
    script = fields.Str(required=True)

# ------------------------ ROUTES ------------------------

@bp.route('/')
def get():
    """     returns a list of Annotations
    """

    return "hello world", 200

# @bp.route('/<int:image_id>/<int:annotation_class_id>')
@bp.route('/<int:image_id>/<int:annotation_class_id>')
class Annotation(MethodView):
    @bp.arguments(GetAnnArgsSchema, location='query')
    @bp.response(200, AnnRespSchema)
    def get(self, args):
        """     returns an Annotation
        """

        return 200

    @bp.arguments(PostAnnArgsSchema, location='json')
    def post(self, args):
        """     process a new annotation

        """

        return 200

    @bp.arguments(PutAnnArgsSchema, location='json')
    def put(self, args):
        """     create or update an annotation directly in the db

        """

        return 201

    @bp.arguments(DeleteAnnArgsSchema, location='query')
    def delete(self, args):
        """     delete an annotation

        """

        return {}, 204

#################################################################################
@bp.route('/<int:image_id>/<int:annotation_class_id>/search')
class SearchAnnotations(MethodView):
    @bp.arguments(GetAnnSearchArgsSchema, location='query')
    @bp.response(200, AnnRespSchema(many=True))
    def get(self, args, image_id, annotation_class_id):
        """Search for annotations

        # Implementation
        - Will need to determine the return type. Should it be pure geojson?
        """

        return {}, 200

#################################################################################
@bp.route('/<int:image_id>/<int:annotation_class_id>/predict')
class PredictAnnotations(MethodView):
    """     request new DL model predictions
    """
    @bp.arguments(PostAnnArgsSchema, location='json')
    @bp.response(201, AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):

        return 200

#################################################################################
@bp.route('/<int:annotation_class_id>/dryrun')
class AnnotationDryRun(MethodView):
    @bp.arguments(PostDryRunArgsSchema, location='json')
    def post(self, args, annotation_class_id):
        """     perform a dry run for the given annotation

        """

        return 200

