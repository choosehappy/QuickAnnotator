from flask_smorest import Blueprint, abort
from flask_smorest.fields import Upload
from marshmallow import fields, Schema
from flask.views import MethodView
from flask import current_app, request, send_from_directory, send_file
from werkzeug.datastructures import FileStorage
from datetime import datetime
from quickannotator.db import db
import openslide as ops
import openslide.deepzoom as deepzoom
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import large_image
import os
import io

import quickannotator.db.models
# from .helper import getTile


bp = Blueprint('image', __name__, description='Image operations')

# ------------------------ RESPONSE MODELS ------------------------
class ImageRespSchema(SQLAlchemyAutoSchema):
    """     Image response schema      """
    class Meta:
        model = quickannotator.db.models.Image

    embedding_coord = quickannotator.db.models.GeometryField()

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
        result = db.session.query(
            *[getattr(quickannotator.db.models.Image, column.name) for column in quickannotator.db.models.Image.__table__.columns],
            db.func.ST_AsGeoJSON(quickannotator.db.models.Image.embedding_coord).label('embedding_coord')
        ).filter(quickannotator.db.models.Image.id == args['image_id']).first()
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

        db.session.query(quickannotator.db.models.Image).filter(id=args['image_id']).delete()
        return 204

#################################################################################
@bp.route('/<int:project_id>/search', endpoint="image_search")
class ImageSearch(MethodView):
    @bp.arguments(SearchImageArgsSchema, location='query')
    @bp.response(200, ImageRespSchema(many=True))
    def get(self, args, project_id):
        """     returns a list of Images
        """
        result = db.session.query(quickannotator.db.models.Image).filter(quickannotator.db.models.Image.project_id == project_id).all()
        return result, 200

#################################################################################
@bp.route('/<int:image_id>/<int:file_type>/file', endpoint="file")
class ImageFile(MethodView):
    def get(self, image_id, file_type):
        """     returns an Image file   """
        result = db.session.query(quickannotator.db.models.Image).filter(quickannotator.db.models.Image.id == image_id).first()

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

        result = db.session.query(quickannotator.db.models.Image).filter(quickannotator.db.models.Image.id == image_id).first()

        if file_type == 1:  # image file
            # TODO implement image file deletion
            pass
        elif file_type == 2:  # thumbnail file
            # TODO implement thumbnail file deletion
            pass
        return 204

#################################################################################

@bp.route('/<int:image_id>/patch_file/<int:level>/<int:col>_<int:row>.<string:file_format>', endpoint="patch")
class PatchFile(MethodView):
    def get(self, image_id, level, col, row, file_format):
        """     returns a patch file   """

        path = quickannotator.db.models.Image.query.get(image_id).path
        full_path = os.path.join(current_app.root_path, path)
        img = large_image.open(full_path)

        # Get the image patch
        patch = img.getTile(col, row, level, pilImageAllowed=True)

        # Create an in-memory bytes buffer
        img_bytes = io.BytesIO()
        patch.save(img_bytes, 'PNG')
        img_bytes.seek(0)

        # Return the image as a PNG file
        return send_file(img_bytes, mimetype='image/png')

