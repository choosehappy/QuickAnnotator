import os
import shutil
import ujson
from tqdm import tqdm
from quickannotator import constants
from quickannotator.db import db_session
from quickannotator.db.fsmanager import fsmanager
from shapely.geometry import shape
from quickannotator.db.crud.image import delete_images, get_image_by_id
from quickannotator.db.crud.tile import TileStoreFactory, TileStore
from quickannotator.constants import IMPORT_ANNOTATION_BATCH_SIZE
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.annotation_class import get_all_annotation_classes_for_project

def import_geojson_annotation_file(image_id: int, annotation_class_id: int, isgt: bool, filepath: str):
    '''
    This is expected to be a geojson feature collection file, with each polygon being a feature.
    
    '''
    # use ujson to read fast
    with open(filepath, 'r', encoding='utf-8') as file:
        # Load the JSON data into a Python dictionary
        # TODO need to switch to orjson after export annotation and landing page merged.
        data = ujson.loads(file.read())
        features = data["features"]


    tile_store: TileStore = TileStoreFactory.get_tilestore()
    annotation_store = AnnotationStore(image_id, annotation_class_id, isgt, in_work_mag=False)
    all_anno = []
    for i, d in enumerate(tqdm(features)):
        all_anno.append(shape(d['geometry']))
        
        if len(all_anno)==IMPORT_ANNOTATION_BATCH_SIZE:
            anns = annotation_store.insert_annotations(all_anno)
            tile_ids = {ann.tile_id for ann in anns}
            tile_store.upsert_gt_tiles(image_id=image_id, annotation_class_id=annotation_class_id, tile_ids=tile_ids)
            db_session.commit()
            all_anno = []
    
    # commit any remaining annotations
    if all_anno:
        anns = annotation_store.insert_annotations(all_anno)
        tile_ids = {ann.tile_id for ann in anns}
        tile_store.upsert_gt_tiles(image_id=image_id, annotation_class_id=annotation_class_id, tile_ids=tile_ids)
        db_session.commit()


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
