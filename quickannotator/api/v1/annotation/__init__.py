from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import shapely.wkt
from sqlalchemy import Table
from shapely.geometry import shape, mapping

import quickannotator.db as qadb
from .helper import annotations_within_bbox, annotations_within_bbox_spatial

bp = Blueprint('annotation', __name__, description='Annotation operations')


# ------------------------ MODELS ------------------------
class AnnRespSchema(SQLAlchemyAutoSchema):
    """     Annotation response schema      """
    class Meta:
        model = qadb.Annotation
        include_fk = True
        exclude = ("image_id", "isgt")
    centroid = qadb.GeometryField()
    polygon = qadb.GeometryField()

class GetAnnArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    annotation_id = fields.Int(required=True)

class GetAnnSearchArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    x1 = fields.Int(required=False)
    y1 = fields.Int(required=False)
    x2 = fields.Int(required=False)
    y2 = fields.Int(required=False)
    polygon = qadb.GeometryField(required=False)

class PostAnnArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    polygon = qadb.GeometryField(required=True)

class OperationArgsSchema(AnnRespSchema):
    operation = fields.Integer(required=True)  # Default 0 for union.
    polygon2 = qadb.GeometryField(required=True)    # The second polygon

class PutAnnArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    annotation_id = fields.Int()
    centroid = qadb.GeometryField(required=True)
    area = fields.Str()
    polygon = qadb.GeometryField(required=True)
    custom_metrics = fields.Dict()

class DeleteAnnArgsSchema(GetAnnArgsSchema):
    pass

class PostDryRunArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    polygon = fields.String(required=True)
    script = fields.Str(required=True)

# ------------------------ ROUTES ------------------------

@bp.route('/<int:image_id>/<int:annotation_class_id>')
class Annotation(MethodView):
    @bp.arguments(GetAnnArgsSchema, location='query')
    @bp.response(200, AnnRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     returns an Annotation
        """
        gtpred = 'gt' if args['is_gt'] else 'pred'
        table_name = f"{image_id}_{annotation_class_id}_{gtpred}_annotation"
        table = Table(table_name, qadb.db.metadata, autoload_with=qadb.db.engine)
        stmt = table.select().where(table.c.id == args['annotation_id']).with_only_columns(
            *(col for col in table.c if col.name != "polygon" and col.name != "centroid"),
            table.c.centroid.ST_AsGeoJSON().label('centroid'),
            table.c.polygon.ST_AsGeoJSON().label('polygon')
        )
        result = qadb.db.session.execute(stmt).first()
        return result, 200

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
        gtpred = 'gt' if args['is_gt'] else 'pred'
        table_name = f"{image_id}_{annotation_class_id}_{gtpred}_annotation"
        table = Table(table_name, qadb.db.metadata, autoload_with=qadb.db.engine)

        if "polygon" in args:
            # search for annotations within the bounding box
            pass
        elif "x1" in args and "y1" in args and "x2" in args and "y2" in args:
            # return all annotations
            return annotations_within_bbox_spatial(table_name, args['x1'], args['y1'], args['x2'], args['y2']), 200
        else:
            stmt = table.select()
            result = qadb.db.session.execute(stmt).fetchall()
            return result, 200
        

#################################################################################
@bp.route('/<int:image_id>/<int:annotation_class_id>/predict')
class PredictAnnotations(MethodView):
    """     request new DL model predictions
    """
    @bp.arguments(PostAnnArgsSchema, location='json')
    @bp.response(200, AnnRespSchema(many=True))
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

@bp.route('/operation')
class AnnotationOperation(MethodView):
    @bp.arguments(OperationArgsSchema, location='json')
    @bp.response(200, AnnRespSchema)
    def post(self, args):
        """     perform a union of two annotations

        """

        poly1 = shape(args['polygon'].geometry)
        poly2 = shape(args['polygon2'].geometry)
        operation = args['operation']

        if operation == 0:
            union = poly1.union(poly2)
        
        resp = AnnRespSchema().dump(args)
        resp['polygon'] = mapping(union)
        resp['area'] = union.area
        resp['centroid'] = union.centroid
        return resp, 200