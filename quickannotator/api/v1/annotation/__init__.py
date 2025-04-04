from flask_smorest import Blueprint
from marshmallow import fields, Schema
from flask.views import MethodView
from shapely.geometry import shape, mapping
import json
from typing import List
import quickannotator.db.models as models
from ..utils.shared_crud import AnnotationStore
import geojson
from flask import Response
from quickannotator.api.v1.utils.shared_crud import write_to_tarfile


bp = Blueprint('annotation', __name__, description='Annotation operations')


# ------------------------ MODELS ------------------------
class AnnRespSchema(Schema):
    """     Annotation response schema      """
    id = fields.Int()
    tile_id = fields.Int()
    centroid = models.GeometryField()
    polygon = models.GeometryField()
    area = fields.Float()
    custom_metrics = fields.Dict()

    datetime = fields.DateTime(format='iso')


class GetAnnArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    annotation_id = fields.Int(required=True)

class GetAnnSearchArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    x1 = fields.Int(required=False)
    y1 = fields.Int(required=False)
    x2 = fields.Int(required=False)
    y2 = fields.Int(required=False)
    polygon = models.GeometryField(required=False)

class GetAnnWithinPolyArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    polygon = models.GeometryField(required=True)

class GetAnnByTileIdsArgsSchema(Schema):
    tile_ids = fields.List(fields.Int(), required=True)
    is_gt = fields.Bool(required=True)

class PostAnnsArgsSchema(Schema):
    polygons = fields.List(models.GeometryField(), required=True)

class OperationArgsSchema(AnnRespSchema):
    operation = fields.Integer(required=True)  # Default 0 for union.
    polygon2 = models.GeometryField(required=True)    # The second polygon

class PutAnnArgsSchema(Schema):
    annotation_id = fields.Int(required=True)
    polygon = models.GeometryField(required=True)
    is_gt = fields.Bool(required=True)

class DeleteAnnArgsSchema(GetAnnArgsSchema):
    pass

class PostDryRunArgsSchema(Schema):
    is_gt = fields.Bool(required=True)
    polygon = fields.String(required=True)
    script = fields.Str(required=True)

class DownloadAnnsArgsSchema(Schema):
    image_ids = fields.List(fields.Int(), required=True)
    annotation_class_ids = fields.List(fields.Int(), required=True)

    format = fields.Str(required=False)  # e.g. 'geojson', 'shp', etc.
    metrics_export_format = fields.Str(required=False)  # e.g. 'csv', 'json', etc.

# ------------------------ ROUTES ------------------------

@bp.route('/<int:image_id>/<int:annotation_class_id>')
class Annotation(MethodView):
    @bp.arguments(GetAnnArgsSchema, location='query')
    @bp.response(200, AnnRespSchema)
    def get(self, args, image_id, annotation_class_id):
        """     returns an Annotation
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        result: models.Annotation = store.get_annotation_by_id(args['annotation_id'])
        return result, 200


    @bp.arguments(PostAnnsArgsSchema, location='json')
    @bp.response(200, AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     post new annotations to the db. 
        
        This method is primarily used for ground truth annotations. Predictions should only by saved by the model.
        """
        polygons: List[geojson.Polygon] = args['polygons']
        store = AnnotationStore(image_id, annotation_class_id, is_gt=True, in_work_mag=False)
        anns = store.insert_annotations([shape(poly) for poly in polygons])

        return anns, 200


    @bp.arguments(PutAnnArgsSchema, location='json')
    @bp.response(201, AnnRespSchema)
    def put(self, args, image_id, annotation_class_id):
        """     create or update an annotation directly in the db
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        ann = store.update_annotation(args['annotation_id'], shape(args['polygon']))

        return ann, 201
    

    @bp.arguments(DeleteAnnArgsSchema, location='query')
    def delete(self, args, image_id, annotation_class_id):
        """     delete an annotation
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'])
        result = store.delete_annotation(args['annotation_id'])

        if result:
            return {}, 204
        else:
            return {"message": "Annotation not found"}, 404
                

@bp.route('/<int:image_id>/<int:annotation_class_id>/tileids')
class AnnotationByTileIds(MethodView):
    @bp.arguments(GetAnnByTileIdsArgsSchema, location='json')
    @bp.response(200, AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     get all annotations for a given tile
        """

        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        anns = store.get_annotations_for_tiles(args['tile_ids'])

        return anns, 200
    

@bp.route('/<int:image_id>/<int:annotation_class_id>/withinpoly')
class AnnotationsWithinPolygon(MethodView):
    @bp.arguments(GetAnnWithinPolyArgsSchema, location='json')
    @bp.response(200, AnnRespSchema(many=True))
    def post(self, args, image_id, annotation_class_id):
        """     get all annotations within a polygon
        """
        store = AnnotationStore(image_id, annotation_class_id, args['is_gt'], in_work_mag=False)
        anns = store.get_annotations_within_poly(shape(args['polygon']))
        return anns, 200


# TODO: This endpoint will be needed when we build in custom scripting.
# @bp.route('/<int:annotation_class_id>/dryrun')
# class AnnotationDryRun(MethodView):
#     @bp.arguments(PostDryRunArgsSchema, location='json')
#     def post(self, args, annotation_class_id):
#         """     perform a dry run for the given annotation

#         """

#         return 200


@bp.route('/operation')
class AnnotationOperation(MethodView):
    @bp.arguments(OperationArgsSchema, location='json')
    @bp.response(200, AnnRespSchema)
    def post(self, args):
        """     perform a union of two annotations

        """

        poly1 = shape(args['polygon'])
        poly2 = shape(args['polygon2'])
        operation = args['operation']

        if operation == 0:
            union = poly1.union(poly2)
        
            resp = {field: args[field] for field in AnnRespSchema().fields.keys() if field in args} # Basically a copy of args without "polygon2" or "operation"
            # unfortunately we have to lose the dictionary format because we are mimicking the geojson string outputted by the db.
            resp['polygon'] = json.dumps(mapping(union))
            resp['centroid'] = json.dumps(mapping(union.centroid))   
            resp['area'] = union.area

        return resp, 200


@bp.route('/export/tar')
class DownloadAnnotations(MethodView):
    @bp.arguments(DownloadAnnsArgsSchema, location='query')
    @bp.response(200, {"format": "binary", "type": "string"}, content_type="application/x-tar")
    def get(self, args):
        """ Export annotations for multiple images and annotation classes as a TAR file """

        image_ids = args['image_ids']
        annotation_class_ids = args['annotation_class_ids']
        format = args.get('format', 'geojson')
        tar_buffer = write_to_tarfile(image_ids, annotation_class_ids, format)
        response = Response(tar_buffer.getvalue(), mimetype="application/x-tar")
        response.headers.set("Content-Disposition", "attachment", filename="annotations.tar.gz")  # Update filename to reflect gzip compression
        return response
