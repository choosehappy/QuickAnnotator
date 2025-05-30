from flask_smorest import abort
from flask.views import MethodView
from flask import current_app, request, send_from_directory, send_file
from sqlalchemy import func
from werkzeug.utils import secure_filename
from quickannotator.constants import ImageType
from quickannotator.db import db_session
import large_image
import openslide as ops
import os
import io
import ujson
import shutil
import quickannotator.db.models as db_models
from . import models as server_models
from flask_smorest import Blueprint
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.image import add_image_by_path
from quickannotator.api.v1.image.utils import import_geojson_annotation_file, delete_annotation_tables_by_image_id
# TODO: fs_manager
projects_path = 'mounts/nas_write/projects'

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
        image_id = args['image_id']
        image = db_session.query(db_models.Image).filter(db_models.Image.id==image_id).first()
        project_id = image.project_id
        print(f'projec_id - {project_id}')
        # delete image's annotation tables
        delete_annotation_tables_by_image_id(image_id)
        # delete image from DB
        db_session.query(db_models.Image).filter(db_models.Image.id == image_id).delete()
        db_session.commit()

        # remove image folder TODO need to save file system path in static variable
        # TODO: fs_manager
        image_path = os.path.join(current_app.root_path, f'data/nas_write/projects/proj_{project_id}/images/img_{image_id}')
        if os.path.exists(image_path):
            try:
                shutil.rmtree(image_path)
            except OSError as e:
                print(f"Error deleting folder '{image_path}': {e}")
        return 204

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

def createTableAndImportAnnotation(image_id: int, annot_file_path):
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
                # TODO: fs_manager
                full_project_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}/images/temp')
                temp_slide_path = os.path.join(full_project_path,filename)
                # save image to temp folder
                os.makedirs(full_project_path, exist_ok=True)
                file.save(temp_slide_path)
                
                # read image info and insert to image table
                new_image = add_image_by_path(project_id, temp_slide_path)
                # move the actual slides file and update the slide path after create image in DB
                # image = db_session.query(db_models.Image).filter_by(name=name, path=temp_slide_path).first()
                image_id = new_image.id
                # TODO: fs_manager
                slide_folder_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}/images/img_{image_id}')
                image_full_path = os.path.join(slide_folder_path, filename)
                # move image file to img_{id} folder
                os.makedirs(slide_folder_path, exist_ok=True)
                shutil.move(temp_slide_path, image_full_path)

                new_image.path = image_full_path
                db_session.add(new_image)
                db_session.commit()

                # import annotation if it exist in temp dir
                # TODO: fs_manager
                annot_file_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}/images/temp/{file_basename}_annotations.json')
                # for geojson
                if os.path.exists(annot_file_path):
                    createTableAndImportAnnotation(image_id, annot_file_path)
                # TODO: fs_manager
                annot_file_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}/images/temp/{file_basename}_annotations.geojson')
                # for geojson
                if os.path.exists(annot_file_path):
                    createTableAndImportAnnotation(image_id, annot_file_path)

            # handle annotation file
            if file_ext in JSON_extensions:
                # TODO: fs_manager
                full_project_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}/images/temp')
                temp_annot_path = os.path.join(full_project_path,filename)

                # save annot to temp folder
                os.makedirs(full_project_path, exist_ok=True)
                file.save(temp_annot_path)
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

        result = db_session.query(db_models.Image).filter(db_models.Image.id == image_id).first()

        if file_type == ImageType.IMAGE:
            # TODO implement image file deletion
            pass
        elif file_type == ImageType.THUMBNAIL:
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

