import shapely.wkb
import shapely.affinity
import cv2, numpy as np
import random

from torch.utils.data import IterableDataset
from quickannotator.db import get_session
from quickannotator.db.crud.tile import TileStoreFactory
from quickannotator.db.crud.annotation_class import get_annotation_class_by_id
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.dl.utils import MaskCacheManager, ImageCacheManager, CacheableImage, CacheableMask, load_tile 

import logging
import os
from datetime import datetime
import quickannotator.constants as constants

logger = logging.getLogger(constants.LoggerNames.RAY.value)

class TileDataset(IterableDataset):
    def __init__(self, classid, boost_count=5):
        self.classid = classid
        self.boost_count = boost_count
        self.image_cache_manager = ImageCacheManager()
        self.mask_cache_manager = MaskCacheManager()
        with get_session() as db_session:  # Ensure this provides a session context
            annotation_class = get_annotation_class_by_id(classid)
            self.magnification = annotation_class.work_mag
            self.tile_size = annotation_class.work_tilesize
        
    def __iter__(self):
        tilestore = TileStoreFactory.get_tilestore()
        
        while tile := tilestore.get_workers_tiles(self.classid, self.boost_count):
            #print(tile)
            #print(f"tile retval 2 {tile}")

            image_id = tile.image_id
            tile_id = tile.tile_id
            img_cache_key = CacheableImage.get_key(image_id, self.classid, tile_id)
            img_cache_val = self.image_cache_manager.get_cached(img_cache_key)
            mask_cache_key = CacheableMask.get_key(image_id, self.classid, tile_id)
            mask_cache_val = self.mask_cache_manager.get_cached(mask_cache_key)

            


            if img_cache_val:
                io_image = img_cache_val.get_image()
                x,y = img_cache_val.get_coordinates()
            else:
                io_image,x,y = load_tile(tile)
                
                self.image_cache_manager.cache(img_cache_key, CacheableImage(io_image, (x, y)))
            

            if mask_cache_val:
                mask_image = mask_cache_val.get_mask()
            else:
                with get_session() as db_session: #TODO: Move down?
                    store = AnnotationStore(image_id, self.classid, is_gt=True, in_work_mag=True, mode=constants.AnnotationReturnMode.WKB)
                    annotations = store.get_annotations_for_tiles(tile_id)
                    db_session.expunge_all()

                    if len(annotations) == 0: # would be strange given how things are set up?
                        continue
            #----
                mask_image = np.zeros((self.tile_size, self.tile_size), dtype=np.uint8) #TODO: maybe should be moved to a project wide available utility function? not sure
                for annotation in annotations:
                    annotation_polygon = shapely.wkb.loads(bytes(annotation.polygon.data))
                    translated_polygon = shapely.affinity.translate(annotation_polygon, xoff=-x, yoff=-y) # need to scale this down from base mag to target mag
                    cv2.fillPoly(mask_image, [np.array(translated_polygon.exterior.coords, dtype=np.int32)], 1)
                
                
                mask_image = (mask_image>0).astype(np.uint8) # if two polygons slightly overlap, fillpoly is addiditve and you end upwith values >1
                
                self.mask_cache_manager.cache(mask_cache_key, CacheableMask(mask_image))

            # Log image dimensions
            logger.debug(f"Image dimensions: {io_image.shape}, Mask dimensions: {mask_image.shape}")

            yield io_image, mask_image

