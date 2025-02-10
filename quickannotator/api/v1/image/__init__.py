from flask_smorest import Blueprint, abort
from flask_smorest.fields import Upload
from marshmallow import fields, Schema
from flask.views import MethodView
from flask import current_app, request, send_from_directory, send_file
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from datetime import datetime
import quickannotator.db as qadb
from quickannotator.db import db
import openslide as ops
import openslide.deepzoom as deepzoom
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import large_image
import os
import io
# from .helper import getTile


bp = Blueprint('image', __name__, description='Image operations')

# ------------------------ RESPONSE MODELS ------------------------
class ImageRespSchema(SQLAlchemyAutoSchema):
    """     Image response schema      """
    class Meta:
        model = qadb.Image

    embedding_coord = qadb.GeometryField()

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
            *[getattr(qadb.Image, column.name) for column in qadb.Image.__table__.columns],
            db.func.ST_AsGeoJSON(qadb.Image.embedding_coord).label('embedding_coord')
        ).filter(qadb.Image.id == args['image_id']).first()
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
        result = db.session.query(qadb.Image).filter(qadb.Image.project_id == project_id).all()
        return result, 200
    
@bp.route('/project/<int:project_id>', endpoint="images")
class ImageSearch(MethodView):
    @bp.arguments(SearchImageArgsSchema, location='query')
    @bp.response(200, ImageRespSchema(many=True))
    def get(self, args, project_id):
        """     returns a list of Images
        """
        # images = db.session.query(qadb.Image).filter(qadb.Image.project_id == project_id).all()
        # if images is not None:
        #     return images
        # else:
        #     abort(404, message="Images not found")
        images = db.session.query(
            *[getattr(qadb.Image, column.name) for column in qadb.Image.__table__.columns],
            db.func.ST_AsGeoJSON(qadb.Image.embedding_coord).label('embedding_coord')
        ).filter(qadb.Image.project_id == project_id).all()
        if images is not None:
            return images, 200
        else:
            abort(404, message="Image not found")

#################################################################################
@bp.route('/upload/files', methods=["POST"])
def upload_files():
    """Upload a file"""
    filenames=[]
    files = request.files.getlist('files')
    
    for file in files:
        filename = secure_filename(file.filename)
        os.makedirs('./upload', exist_ok=True)
        filepath = os.path.join('./upload',filename)
        file.save(filepath)
        filenames.append(filename)
        print(filename)

    return 'file uploaded successfully'


@bp.route('/<int:image_id>/<int:file_type>/file', endpoint="file")
class ImageFile(MethodView):
    def get(self, image_id, file_type):
        """     returns an Image file   """
        result = db.session.query(qadb.Image).filter(qadb.Image.id == image_id).first()
        full_path = os.path.join(current_app.root_path, result.path)
        if file_type == 1:  # image file
            return send_from_directory(full_path, result.name)
        elif file_type == 2:    # thumbnail file
            try:
                slide = ops.OpenSlide(full_path)
                thumbnail = slide.get_thumbnail((256, 256))
            except ops.OpenSlideError as e:
                print("Error opening slide:", e)
            # Save thumbnail to bytes buffer
            img_buffer = io.BytesIO()
            thumbnail.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            return send_file(img_buffer, mimetype='image/png')



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

@bp.route('/<int:image_id>/patch_file/<int:level>/<int:col>_<int:row>.<string:file_format>', endpoint="patch")
class PatchFile(MethodView):
    def get(self, image_id, level, col, row, file_format):
        """     returns a patch file   """

        path = qadb.Image.query.get(image_id).path
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

