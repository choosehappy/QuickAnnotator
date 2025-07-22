import os
import shutil

from quickannotator import constants
from quickannotator.db import db_session
from quickannotator.db.fsmanager import fsmanager

from quickannotator.db.crud.image import delete_images, get_image_by_id
from quickannotator.db.crud.tile import TileStoreFactory

from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.annotation_class import get_all_annotation_classes_for_project


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
