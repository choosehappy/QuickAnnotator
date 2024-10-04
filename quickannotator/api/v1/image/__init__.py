import openslide.deepzoom
from flask_smorest import Blueprint, abort
from flask_smorest.fields import Upload
from marshmallow import fields, Schema
from flask.views import MethodView
from flask import current_app, request, send_from_directory
from werkzeug.datastructures import FileStorage
from datetime import datetime
import quickannotator.db as qadb
from quickannotator.db import db
import openslide as ops


bp = Blueprint('image', __name__, description='Image operations')

# ------------------------ RESPONSE MODELS ------------------------
class ImageRespSchema(Schema):
    """     Image response schema      """
    id = fields.Int()
    name = fields.Str()
    path = fields.Str()
    height = fields.Int()
    width = fields.Int()
    datetime = fields.DateTime()

class GetImageArgsSchema(Schema):
    image_id = fields.Int(required=True)

class SearchImageArgsSchema(Schema):
    pass

class PostImageArgsSchema(Schema):
    name = fields.Str(required=True)
    path = fields.Str(required=True)
    embedding_coord = fields.Str(required=False)
    group_id = fields.Int(required=False)
    split = fields.Int(required=False)

class DeleteImageArgsSchema(GetImageArgsSchema):
    pass

class UploadFileArgsSchema(Schema):
    file = Upload(required=True)

# ------------------------ ROUTES ------------------------
@bp.route('/', endpoint="image")
class Image(MethodView):
    @bp.arguments(GetImageArgsSchema, location='query')
    @bp.response(200, ImageRespSchema)
    def get(self, args):
        """     returns an Image
        """
        result = db.session.query(qadb.Image).filter(qadb.Image.id == args['image_id']).first()
        if result is not None:
            return result, 200
        else:
            abort(404, message="Image not found")


    @bp.arguments(PostImageArgsSchema, location='query')
    @bp.response(200, description="Image created")
    def post(self, args):
        """     upload an Image

        TODO: implement image upload
        """

        return 200

    @bp.arguments(DeleteImageArgsSchema, location='query')
    @bp.response(204, description="Image  deleted")
    def delete(self, args):
        """     delete an Image   """

        db.session.query(qadb.Image).filter(id=args['image_id']).delete()
        return 204

#################################################################################
@bp.route('/<int:project_id>/search', endpoint="image_search")
class ImageSearch(MethodView):
    @bp.arguments(SearchImageArgsSchema, location='query')
    @bp.response(200, ImageRespSchema(many=True))
    def get(self, args, project_id):
        """     returns a list of Images
        """
        result = db.session.query(qadb.Image).filter(qadb.Image.proj_id == project_id).all()
        return result, 200

#################################################################################
@bp.route('/<int:image_id>/<int:file_type>/file', endpoint="file")
class ImageFile(MethodView):
    def get(self, image_id, file_type):
        """     returns an Image file   """
        result = db.session.query(qadb.Image).filter(qadb.Image.id == image_id).first()

        if file_type == 1:  # image file
            return send_from_directory(result['path'], result['name'])
        elif file_type == 2:    # thumbnail file
            # TODO implement thumbnail file
            pass


    @bp.arguments(UploadFileArgsSchema, location='files')
    def put (self, args, image_id, file_type):
        """     upload an Image file
        TODO: implement image file upload
        """

        return 201

    def delete(self, image_id, file_type):
        """     delete an Image file   """

        result = db.session.query(qadb.Image).filter(qadb.Image.id == image_id).first()

        if file_type == 1:  # image file
            # TODO implement image file deletion
            pass
        elif file_type == 2:  # thumbnail file
            # TODO implement thumbnail file deletion
            pass
        return 204

#################################################################################

@bp.route('/<int:image_id>/patch_file/<int:level>/<int:col>_<int:row>.<int:file_format>', endpoint="patch")
class PatchFile(MethodView):
    def get(self, image_id, level, col, row, file_format):
        """     returns a patch file   """

        result = db.session.query(qadb.Image).filter(qadb.Image.id == image_id).first()
        slide = ops.OpenSlide(result['path'])
        dz = openslide.deepzoom.DeepZoomGenerator(slide)
        tile = dz.get_tile(level, (col, row))
        return tile, 200
