import os
import shutil
from werkzeug.datastructures import FileStorage
from quickannotator import constants
from quickannotator.db import db_session
from quickannotator.db.fsmanager import fsmanager
import large_image


from quickannotator.db.crud.image import delete_images, get_image_by_id, add_image_by_path, get_image_by_name_case_insensitive, is_dicom_tilesource
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
    is_dicom = is_dicom_tilesource(large_image.getTileSource(temp_filepath))
    new_image = add_image_by_path(project_id, temp_filepath, is_dicom=is_dicom)
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

def _import_annotations_from_temp(image_id, file_basename):
    """Import any annotations found in the temp directory for the given image basename."""
    annotation_classes = list(get_all_annotation_classes())
    db_session.expunge_all()
    for annot_cls in annotation_classes:
        annot_cls_name = annot_cls.name
        annot_cls_id = annot_cls.id
        for fmt in constants.AnnotationFileFormats:
            temp_path = fsmanager.nas_write.get_temp_path(relative=False)
            annotation_filename = fsmanager.nas_write.construct_annotation_file_name(file_basename, annot_cls_name, fmt.value)
            annot_filepath = os.path.join(temp_path, annotation_filename)
            if os.path.exists(annot_filepath):
                logger.info(f"Found image annotation file - {annot_filepath}")
                import_annotations(image_id, annot_cls_id, True, annot_filepath)


def import_image_from_dicom_wsi(project_id: int, files: list[FileStorage], folder_name: str) -> dict:
    """Import a DICOM WSI folder as a single image entry."""
    
    temp_path = fsmanager.nas_write.get_temp_path(relative=False)
    dicom_subfolder_path = os.path.join(temp_path, folder_name)
    os.makedirs(dicom_subfolder_path, exist_ok=True)
    
    # Save all uploaded files to temp directory
    saved_files = []
    for file in files:
        temp_filepath = os.path.join(dicom_subfolder_path, file.filename)
        try:
            file.save(temp_filepath)
            saved_files.append((file.filename, temp_filepath))
        except Exception as e:
            logger.info(f"Error saving file {file.filename}: {e}")
    
    if not saved_files:
        logger.info(f"No files were saved from folder {folder_name}")
        return {'type': 'dcm', 'name': folder_name}
    
    # Find the largest file to use as the primary image file
    largest_file = max(saved_files, key=lambda x: os.path.getsize(x[1]))
    largest_filename = largest_file[0]
    largest_filepath = largest_file[1]
    
    # Check for duplicate by folder name
    existing_image = get_image_by_name_case_insensitive(project_id, folder_name)
    if existing_image:
        logger.info(f"Image '{folder_name}' already exists. Skipping folder upload")
        return {'type': 'dcm', 'name': folder_name}
    
    # Check if the largest file is a valid DICOM WSI
    slide = large_image.getTileSource(largest_filepath)
    if not is_dicom_tilesource(slide):
        logger.info(f"The largest file '{largest_filename}' is not a valid DICOM WSI. Skipping folder upload")
        return {'type': 'dcm', 'name': folder_name}

    # Create image entry in DB
    new_image = add_image_by_path(project_id, largest_filepath, is_dicom=True)
    db_session.add(new_image)
    db_session.commit()
    image_id = new_image.id
    
    # Create the image folder and DICOM subdirectory
    slide_folder_path = fsmanager.nas_write.get_project_image_path(project_id, image_id, relative=False)
    dicom_subfolder_path = os.path.join(slide_folder_path, folder_name)
    os.makedirs(dicom_subfolder_path, exist_ok=True)
    
    # Move all files from temp to the DICOM subdirectory
    image_full_path = os.path.join(dicom_subfolder_path, largest_filename)
    for filename, temp_filepath in saved_files:
        dest_path = os.path.join(dicom_subfolder_path, filename)
        shutil.move(temp_filepath, dest_path)
    
    # Update image path to point to the largest file
    new_image.path = image_full_path
    db_session.add(new_image)
    db_session.commit()
        
    # Import annotations from temp dir (shared logic)
    file_basename, _ = os.path.splitext(largest_filename)
    _import_annotations_from_temp(image_id, file_basename)
    
    return {'type': 'dcm', 'name': folder_name}


def import_image_from_wsi(project_id:int ,file: FileStorage):
    filename = file.filename
    # get file extension
    file_basename, file_ext = os.path.splitext(filename)
    logger.info(f"Import image {filename}:")
    if get_image_by_name_case_insensitive(project_id, filename):
        logger.info(f"Image {filename} already exists. Skipping image upload")
        return
    image_id = save_image_from_file(project_id, file)

    # Import annotations from temp dir
    _import_annotations_from_temp(image_id, file_basename)