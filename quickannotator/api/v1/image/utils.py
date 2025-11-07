import os
import shutil
from werkzeug.datastructures import FileStorage
from quickannotator import constants
from quickannotator.db import db_session
from quickannotator.db.fsmanager import fsmanager

from quickannotator.db.crud.image import delete_images, get_image_by_id, add_image_by_path, get_image_by_name_case_insensitive
from quickannotator.db.crud.tile import TileStoreFactory
import logging
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.annotation_class import get_all_annotation_classes_for_project, get_all_annotation_classes
from quickannotator.api.v1.annotation.utils import import_annotations
# logger
logger = logging.getLogger(constants.LoggerNames.FLASK.value)

def save_image_from_file(project_id: int, file: FileStorage) -> int:
    filename = file.filename
    temp_path = fsmanager.nas_write.get_temp_path(relative=False)
    temp_filepath = os.path.join(temp_path, filename)

    # save image to temp folder
    os.makedirs(temp_path, exist_ok=True)
    try:
        file.save(temp_filepath)
    except IOError as e:
        logger.info(f"Saving Image Error: An I/O error occurred when saving {filename}: {e}")
    except Exception as e:
        logger.info(f"Saving Image Error: An unexpected error occurred when saving {filename}: {e}")    
    
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
    
    return image_id

def delete_image_and_related_data(image_id):
    image = get_image_by_id(image_id)
    project_id = image.project_id
    annotation_class_ids = [annotation_class.id for annotation_class in get_all_annotation_classes_for_project(project_id)]

    # Delete existing annotations
    AnnotationStore.bulk_drop_tables([image.id], annotation_class_ids + [constants.MASK_CLASS_ID])

    # Delete all respective tiles
    # TODO: consider using cascaded delete
    tile_store = TileStoreFactory.get_tilestore()
    tile_store.delete_tiles(image_ids=image_id)

    # Clean up the file structure
    remove_image_folders(project_id, image_id)

    # Delete the image
    delete_images(image_id)
    

def remove_image_folders(project_id: int, image_id: int):
    # remove the image folders
    full_image_path = fsmanager.nas_write.get_project_image_path(project_id, image_id, relative=False)
    if os.path.exists(full_image_path):
        try:
            shutil.rmtree(full_image_path)
        except OSError as e:
            print(f"Error deleting folder '{full_image_path}': {e}")

def import_image_from_wsi(project_id:int ,file: FileStorage):
    filename = file.filename
    # get file extension
    file_basename, file_ext = os.path.splitext(filename)
    logger.info(f"Import image {filename}:")
    if get_image_by_name_case_insensitive(project_id, filename):
        logger.info(f"Image {filename} already exists. Skipping image upload")
        return
    image_id = save_image_from_file(project_id, file)

    # get all annotation class name
    annotation_classes = list(get_all_annotation_classes())
    db_session.expunge_all()
    breakpoint()
    # import annotation if it exist in temp dir
    for annot_cls in annotation_classes:
        annot_cls_name = annot_cls.name
        annot_cls_id = annot_cls.id
        for format in constants.AnnotationFileFormats:
            temp_path = fsmanager.nas_write.get_temp_path(relative=False)
            annotation_filename = fsmanager.nas_write.construct_annotation_file_name(file_basename, annot_cls_name, format.value)
            annot_filepath = os.path.join(temp_path, annotation_filename)
            # breakpoint()
            # for geojson
            if os.path.exists(annot_filepath):
                logger.info(f"Found image annotation file - {annot_filepath}")
                import_annotations(image_id, annot_cls_id, True, annot_filepath)
