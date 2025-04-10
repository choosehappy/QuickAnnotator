from flask_smorest import abort
from flask.views import MethodView
from flask import current_app, send_from_directory, send_file
from sqlalchemy import func
from quickannotator.db import db_session
import large_image
import os
import io

import quickannotator.db.models as db_models
from . import models as server_models
from flask_smorest import Blueprint

bp = Blueprint('image', __name__, description='Image operations')

@bp.route('/', endpoint="image")
class Image(MethodView):
    @bp.arguments(server_models.GetImageArgsSchema, location='query')
    @bp.response(200, server_models.ImageRespSchema)
    def get(self, args):
        """     returns an Image
        """
        result = db_session.query(
            *[getattr(db_models.Image, column.name) for column in db_models.Image.__table__.columns],
            func.ST_AsGeoJSON(db_models.Image.embedding_coord).label('embedding_coord')
        ).filter(db_models.Image.id == args['image_id']).first()
        if result is not None:
            return result, 200
        else:
            abort(404, message="Image not found")


    @bp.arguments(server_models.PostImageArgsSchema, location='query')
    @bp.response(200, description="Image created")
    def post(self, args):
        """     upload an Image

        TODO: implement image upload
        """

        return 200

    @bp.arguments(server_models.DeleteImageArgsSchema, location='query')
    @bp.response(204, description="Image  deleted")
    def delete(self, args):
        """     delete an Image   """

        db_session.query(db_models.Image).filter(id=args['image_id']).delete()
        return 204

#################################################################################
@bp.route('/<int:project_id>/search', endpoint="image_search")
class ImageSearch(MethodView):
    @bp.arguments(server_models.SearchImageArgsSchema, location='query')
    @bp.response(200, server_models.ImageRespSchema(many=True))
    def get(self, args, project_id):
        """     returns a list of Images
        """
        result = db_session.query(db_models.Image).filter(db_models.Image.project_id == project_id).all()
        return result, 200

#################################################################################
@bp.route('/<int:image_id>/<int:file_type>/file', endpoint="file")
class ImageFile(MethodView):
    def get(self, image_id, file_type):
        """     returns an Image file   """
        result = db_session.query(db_models.Image).filter(db_models.Image.id == image_id).first()

        if file_type == 1:  # image file
            return send_from_directory(result['path'], result['name'])
        elif file_type == 2:    # thumbnail file
            # TODO implement thumbnail file
            pass


    @bp.arguments(server_models.UploadFileArgsSchema, location='files')
    def put (self, args, image_id, file_type):
        """     upload an Image file
        TODO: implement image file upload
        """

        return 201

    def delete(self, image_id, file_type):
        """     delete an Image file   """

        result = db_session.query(db_models.Image).filter(db_models.Image.id == image_id).first()

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

        path = db_models.Image.query.get(image_id).path
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

