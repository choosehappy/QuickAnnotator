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
import shutil
import json
import quickannotator.db.models as db_models
from . import models as server_models
from flask_smorest import Blueprint

projects_path = 'data/nas_write/projects'

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

        db_session.query(db_models.Image).filter(db_models.Image.id == args['image_id']).delete()
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
    @bp.route('/project/<int:project_id>', endpoint="images")
    class ImageSearch(MethodView):
        @bp.arguments(server_models.SearchImageArgsSchema, location='query')
        @bp.response(200, server_models.ImageRespSchema(many=True))
        def get(self, args, project_id):
            """     returns a list of Images
            """
            # images = db.session.query(qadb.Image).filter(qadb.Image.project_id == project_id).all()
            # if images is not None:
            #     return images
            # else:
            #     abort(404, message="Images not found")
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

def import_geojson_annotation_file(image_id, annotation_class_id, gtpred, filepath):
    '''
    This is expected to be a geojson feature collection file, with each polygon being a feature.
    
    '''
    # path = filepath.split("quickannotator/")[1]
    with open(filepath, 'r') as file:
        # Load the JSON data into a Python dictionary
        data = json.load(file)["features"]
    all_anno = []
    
    table_name = f"{image_id}_{annotation_class_id}_{gtpred}_annotation"
    
    
    for i, d in enumerate(tqdm(data)):

        shapely_geometry = shape(d['geometry'])
        annotation = {
            "image_id": image_id,
            "annotation_class_id": annotation_class_id,
            "isgt": gtpred == "gt",
            "centroid": shapely_geometry.centroid.wkt,
            "area": shapely_geometry.area,
            "polygon": shapely_geometry.wkt,
            "custom_metrics": json.dumps({"iou": 0.5}) 
        }
        
        all_anno.append(annotation)
        
        if len(all_anno)==1_000:
            table = Table(table_name, Base.metadata, autoload_with=engine)
            stmt = insert(table).values(all_anno)
            db_session.execute(stmt)
            db_session.commit()
            all_anno = []
    
    # commit any remaining annotations

    table = Table(table_name, Base.metadata, autoload_with=engine)
    stmt = insert(table).values(all_anno)
    db_session.execute(stmt)
    db_session.commit()

def create_annotation_table(image_id, annotation_class_id, gtpred):
    table_name = f"{image_id}_{annotation_class_id}_{gtpred}_annotation"
    table = models.Annotation.__table__.to_metadata(Base.metadata, name=table_name)
    Base.metadata.create_all(bind=engine, tables=[table])

@bp.route('/upload/file', methods=["POST"])
def upload_files():
    """Upload a file"""
    
    file = request.files["file"]
    project_id = request.form.get('project_id')
    print('upload_files ~~~~~~~~~')
    print(project_id)
    if file and project_id:
        filename = secure_filename(file.filename)

        # get file extension
        file_basename, file_ext = os.path.splitext(filename)
        file_ext = file_ext[1:]
        # handle image file
        if file_ext in WSI_extensions:
            full_project_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}/images/temp')
            temp_slide_path = os.path.join(full_project_path,filename)
            # save image to temp folder
            os.makedirs(full_project_path, exist_ok=True)
            file.save(temp_slide_path)
            
            # read image info and insert to image table
            slide = large_image.getTileSource(temp_slide_path)
            image = db_models.Image(project_id=project_id,
                        name=filename,
                        path=temp_slide_path,
                        base_height=slide.sizeY,
                        base_width=slide.sizeX,
                        dz_tilesize=slide.tileWidth,
                        embedding_coord="POINT (1 1)",
                        group_id=0,
                        split=0
                        )
            db_session.add(image)
            db_session.commit()
        
            image = db_session.query(db_models.Image).filter_by(name=filename, path=temp_slide_path).first()
            image_id = image.id
            slide_folder_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}/images/img_{image_id}')
            image_full_path = os.path.join(slide_folder_path, filename)
            # move image file to img_{id} folder
            os.makedirs(slide_folder_path, exist_ok=True)
            shutil.move(temp_slide_path, image_full_path)

            image.path = image_full_path
            db_session.add(image)
            db_session.commit()

            # TODO import annotation if it exist in temp dir
            annot_file_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}/images/temp/{file_basename}_annotations.json')
            print(annot_file_path)
            if os.path.exists(annot_file_path):
                print(f"json File exists: {annot_file_path}")
                create_annotation_table(image_id, 2, 'gt')
                import_geojson_annotation_file(image_id, 2, 'gt', annot_file_path)
            annot_file_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}/images/temp/{file_basename}_annotations.geojson')
            print(annot_file_path)
            if os.path.exists(annot_file_path):
                print(f"geojson File exists: {annot_file_path}")
                create_annotation_table(image_id, 2, 'gt')
                import_geojson_annotation_file(image_id, 2, 'gt', annot_file_path)
            # TODO move 
            

        # handle annotation file
        if file_ext in JSON_extensions:
            full_project_path = os.path.join(current_app.root_path, projects_path, f'proj_{project_id}/images/temp')
            temp_annot_path = os.path.join(full_project_path,filename)

            # save annot to temp folder
            os.makedirs(full_project_path, exist_ok=True)
            file.save(temp_annot_path)
        

        return 'file uploaded successfully'
    
    return 'error'
    
@bp.route('/<int:image_id>/<int:file_type>/file', endpoint="file")
class ImageFile(MethodView):
    def get(self, image_id, file_type):
        """     returns an Image file   """
        result = db_session.query(db_models.Image).filter(db_models.Image.id == image_id).first()
        full_path = os.path.join(current_app.root_path, result.path)

        if file_type == ImageType.IMAGE:
            return send_from_directory(full_path, result['name'])
        elif file_type == ImageType.THUMBNAIL:
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

