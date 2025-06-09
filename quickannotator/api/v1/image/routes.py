from flask_smorest import abort
from flask.views import MethodView
from flask import current_app, request, send_from_directory, send_file
from sqlalchemy import func
from werkzeug.utils import secure_filename
from quickannotator.constants import ImageType, AnnotationFileFormats
from quickannotator.db import db_session
from quickannotator.db.fsmanager import fsmanager
import large_image
import openslide as ops
import os
import io

from quickannotator.db.crud.image import get_image_by_id
import shutil
import quickannotator.db.models as db_models
from . import models as server_models
from flask_smorest import Blueprint
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.image import add_image_by_path
from quickannotator.api.v1.image.utils import delete_image_and_related_data, import_geojson_annotation_file

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
        delete_image_and_related_data(args['image_id'])
        return {}, 204

#################################################################################
@bp.route('/<int:project_id>/search', endpoint="image_search")
class ImageSearch(MethodView):
    @bp.arguments(server_models.SearchImageArgsSchema, location='query')
    @bp.response(200, server_models.ImageRespSchema(many=True))
    def get(self, args, project_id):
        """     returns a list of Images
        """
        images = db_session.query(
            *[getattr(db_models.Image, column.name) for column in db_models.Image.__table__.columns],
            func.ST_AsGeoJSON(db_models.Image.embedding_coord).label('embedding_coord')
        ).filter(db_models.Image.project_id == project_id).all()
        if images is not None:
            return images, 200
        else:
            abort(404, message="Image not found")
#################################################################################
WSI_extensions = ['svs', 'tif','dcm','vms', 'vmu', 'ndpi',
                  'scn', 'mrxs','tiff','svslide','bif','czi']
JSON_extensions = ['json','geojson']

def import_annotations(image_id: int, annot_file_path):
    store = AnnotationStore(image_id, 1, is_gt=True, create_table=True)
    import_geojson_annotation_file(image_id, 1, isgt=True, filepath=annot_file_path)

@bp.route('/upload')
class FileUpload(MethodView):
    @bp.arguments(server_models.UploadFileArgsSchema, location='form')
    @bp.response(200, server_models.UploadFileSchema)
    def post(self, args):
        """Upload a file"""
        file = request.files['file']
        project_id = args["project_id"]
        if file and project_id:
            filename = secure_filename(file.filename)

            # get file extension
            file_basename, file_ext = os.path.splitext(filename)
            file_ext = file_ext[1:]
            # handle image file
            if file_ext in WSI_extensions:
                temp_path = fsmanager.nas_write.get_temp_image_path(relative=False)
                temp_filepath = os.path.join(temp_path,filename)

                # save image to temp folder
                os.makedirs(temp_path, exist_ok=True)
                file.save(temp_filepath)
                
                # read image info and insert to image table
                new_image = add_image_by_path(project_id, temp_filepath)
                # move the actual slides file and update the slide path after create image in DB
                # image = db_session.query(db_models.Image).filter_by(name=name, path=temp_slide_path).first()
                image_id = new_image.id
                slide_folder_path = fsmanager.nas_write.get_project_image_path(project_id, image_id, relative=False)
                image_full_path = os.path.join(slide_folder_path, filename)
                # move image file to img_{id} folder
                os.makedirs(slide_folder_path, exist_ok=True)
                shutil.move(temp_filepath, image_full_path)

                new_image.path = image_full_path
                db_session.add(new_image)
                db_session.commit()

                # import annotation if it exist in temp dir
                for format in AnnotationFileFormats:
                    temp_image_path = fsmanager.nas_write.get_temp_image_path(relative=False)
                    annot_filepath = os.path.join(temp_image_path, f'{file_basename}_annotations.{format.value}')
                    # for geojson
                    if os.path.exists(annot_filepath):
                        import_annotations(image_id, annot_filepath)
            # handle annotation file
            if file_ext in JSON_extensions:
                temp_image_path = fsmanager.nas_write.get_temp_image_path(relative=False)
                annot_filepath = os.path.join(temp_image_path, filename)

                # save annot to temp folder
                os.makedirs(temp_image_path, exist_ok=True)
                file.save(annot_filepath)
            return {'name':filename}, 200
        else:
            abort(404, message="No project id foundin Args")
    
@bp.route('/<int:image_id>/<int:file_type>/file', endpoint="file")
class ImageFile(MethodView):
    def get(self, image_id, file_type):
        """     returns an Image file   """
        result = db_session.query(db_models.Image).filter(db_models.Image.id == image_id).first()
        full_path = os.path.join(current_app.root_path, result.path)

        if file_type == ImageType.IMAGE:
            return send_from_directory(full_path, result['name'])
        elif file_type == ImageType.THUMBNAIL:
            slide = large_image.open(full_path)
            thumbnail, mimeType = slide.getThumbnail(format='PNG',width=256,height=256)
            # Save thumbnail to bytes buffer
            img_buffer = io.BytesIO()
            thumbnail.save(img_buffer, 'PNG')
            img_buffer.seek(0)
            return send_file(img_buffer, mimetype='image/png')

    @bp.arguments(server_models.UploadFileArgsSchema, location='files')
    def put (self, args, image_id, file_type):
        """     upload an Image file
        TODO: implement image file upload
        """

        return 201

    def delete(self, image_id, file_type):
        """     delete an Image file   """

        result = get_image_by_id(image_id)

        if file_type == ImageType.IMAGE:
            # TODO implement image file deletion
            pass
        elif file_type == ImageType.THUMBNAIL:
            # TODO implement thumbnail file deletion
            pass
        return {}, 204

#################################################################################

@bp.route('/<int:image_id>/patch_file/<int:level>/<int:col>_<int:row>.<string:file_format>', endpoint="patch")
class PatchFile(MethodView):
    def get(self, image_id, level, col, row, file_format):
        """     returns a patch file   """

        path = get_image_by_id(image_id).path
        full_path = fsmanager.nas_read.relative_to_global(path)
        img = large_image.open(full_path)
        # Get the image patch
        patch = img.getTile(col, row, level, pilImageAllowed=True)

        # Create an in-memory bytes buffer
        img_bytes = io.BytesIO()
        patch.save(img_bytes, 'PNG')
        img_bytes.seek(0)

        # Return the image as a PNG file
        return send_file(img_bytes, mimetype='image/png')

@bp.route('/<int:image_id>/metadata', endpoint="image_metadata")
class ImageMetadata(MethodView):
    @bp.response(200, server_models.ImageMetadataRespSchema)
    def get(self, image_id):
        """     returns metadata of an Image   """
        result = get_image_by_id(image_id)
        if result is not None:
            full_path = os.path.join(current_app.root_path, result.path)
            try:
                img = large_image.open(full_path)
                metadata = img.getMetadata()
                return {
                    "mpp": metadata.get("mm_x") * 1000  # Convert to microns per pixel
                }, 200
            except Exception as e:
                abort(500, message=f"Error retrieving metadata: {str(e)}")
        else:
            abort(404, message="Image metadata not found")
