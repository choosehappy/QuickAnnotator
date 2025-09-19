from itertools import product
import os
import shutil
from quickannotator.db.fsmanager import fsmanager
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.annotation_class import delete_annotation_classes
from quickannotator.db.crud.image import delete_images
from quickannotator.db.crud.project import delete_projects, get_project_by_id
from quickannotator.db.crud.tile import TileStoreFactory
import quickannotator.constants as constants
from werkzeug.datastructures import FileStorage

def save_tsv_to_temp_dir(project_id: int, file: FileStorage):
    # save tsv under current project folder
    project_path = fsmanager.nas_write.get_project_path(project_id=project_id ,relative=False)
    tsv_filepath = os.path.join(project_path, file.filename)
    os.makedirs(project_path, exist_ok=True)

    try:
        file.save(tsv_filepath)
    except IOError as e:
        print(f"Saving TSV File Error: An I/O error occurred when saving ${file.filename}: {e}")
    except Exception as e:
        print(f"Saving TSV File Error: An unexpected error occurred when saving ${file.filename}: {e}")
    
    return tsv_filepath
    

def delete_project_and_related_data(project_id):
    project = get_project_by_id(project_id)
    
    image_ids = [image.id for image in project.images]

    # This will not include the tissue mask, which is application-level.
    annotation_class_ids = [annotation_class.id for annotation_class in project.annotation_classes]

    # Ensure the mask class ID is included in the deletion
    AnnotationStore.bulk_drop_tables(image_ids, annotation_class_ids + [constants.MASK_CLASS_ID])

    # Delete all respective tiles
    # TODO: consider using cascaded delete
    tile_store = TileStoreFactory.get_tilestore()
    tile_store.delete_tiles(annotation_class_ids=annotation_class_ids)

    # Delete all respective images
    # TODO: consider using cascaded delete
    delete_images(image_ids)

    # Delete the annotation classes
    # TODO: consider using cascaded delete
    delete_annotation_classes(annotation_class_ids)

    # Clean up the file structure
    remove_project_folders(project_id)

    # Delete the project
    delete_projects(project_id)


def remove_project_folders(project_id: int):    # NOTE: This currently does not remove annotation class folders as these are not subfolders of the project.
    # remove the project folders
    full_project_path = fsmanager.nas_write.get_project_path(project_id, relative=False)
    if os.path.exists(full_project_path):
        try:
            shutil.rmtree(full_project_path)
        except OSError as e:
            print(f"Error deleting folder '{full_project_path}': {e}")