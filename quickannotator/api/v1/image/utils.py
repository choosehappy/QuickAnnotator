import ujson
from tqdm import tqdm
from quickannotator.db import db_session
from shapely.geometry import shape
from quickannotator.db.crud.tile import TileStoreFactory, TileStore
from quickannotator.constants import BATCH_SIZE
from quickannotator.db.crud.annotation import AnnotationStore
def import_geojson_annotation_file(image_id: int, annotation_class_id: int, isgt: bool, filepath: str):
    '''
    This is expected to be a geojson feature collection file, with each polygon being a feature.
    
    '''
    # use ujson to read fast
    with open(filepath, 'r', encoding='utf-8') as file:
        # Load the JSON data into a Python dictionary
        data = ujson.loads(file.read())
        features = data["features"]


    tile_store: TileStore = TileStoreFactory.get_tilestore()
    annotation_store = AnnotationStore(image_id, annotation_class_id, isgt, in_work_mag=False)
    all_anno = []
    for i, d in enumerate(tqdm(features)):
        all_anno.append(shape(d['geometry']))
        
        if len(all_anno)==BATCH_SIZE:
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

