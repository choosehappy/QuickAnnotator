from quickannotator.db import models, db_session
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.annotation_class import delete_annotation_classes, get_annotation_class_by_id
from quickannotator.db.crud.image import get_images_for_project
from quickannotator.db.crud.tile import TileStore, TileStoreFactory
from quickannotator.db.fsmanager import fsmanager
import os
import shutil


def delete_annotation_class_and_related_data(annotation_class_id) -> models.AnnotationClass:
    annotation_class = get_annotation_class_by_id(annotation_class_id)

    # Drop all respective annotation tables
    project_id = annotation_class.project_id
    images = get_images_for_project(project_id)
    image_ids = [image.id for image in images]

    AnnotationStore.bulk_drop_tables(image_ids, [annotation_class_id])

    # Clean up tiles
    # TODO: consider using cascaded delete
    tile_store: TileStore = TileStoreFactory.get_tilestore()
    tile_store.delete_tiles(annotation_class_ids=[annotation_class_id])

    # Delete the annotation class
    delete_annotation_classes(annotation_class_id)


def remove_annotation_class_folders(annotation_class_id: int):
    # Remove the annotation class folders
    annotation_class_path = fsmanager.nas_write.get_annotation_class_path(annotation_class_id, relative=False)
    if os.path.exists(annotation_class_path):
        try:
            shutil.rmtree(annotation_class_path)
        except OSError as e:
            print(f"Error deleting folder '{annotation_class_path}': {e}")