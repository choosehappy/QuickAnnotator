import ujson
from tqdm import tqdm
from quickannotator.db import db_session
from shapely.geometry import shape
from quickannotator.db.crud.image import get_image_by_id
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

def drop_annotation_tables_by_image_id(image_id: int):
    # get all annotation class ids
    image = get_image_by_id(image_id)
    annotation_classes = get_all_annotation_classes_for_project(image.project_id)
    for anno_class in annotation_classes:
        try: 
            gt_store = AnnotationStore(image_id.id, anno_class.id, is_gt=True)
        except Exception as e:
            continue
        gt_store.drop_table()

        try: 
            pred_store = AnnotationStore(image_id.id, anno_class.id, is_gt=False)
        except Exception as e:
            continue
        pred_store.drop_table()

