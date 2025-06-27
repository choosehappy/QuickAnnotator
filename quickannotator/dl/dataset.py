import shapely.wkb
import cv2, numpy as np

import scipy.ndimage
from torch.utils.data import IterableDataset
from quickannotator.db import get_session
from quickannotator.db.crud.tile import TileStoreFactory
from quickannotator.db.crud.annotation_class import get_annotation_class_by_id
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.dl.utils import MaskCacheManager, ImageCacheManager, CacheableImage, CacheableMask, load_tile 
import logging
import quickannotator.constants as constants

logger = logging.getLogger(constants.LoggerNames.RAY.value)

class TileDataset(IterableDataset):
    def __init__(self, classid, transforms=None, edge_weight=0, boost_count=5):
        self.classid = classid
        self.transforms = transforms
        self.edge_weight = edge_weight
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
            img_cache_key = CacheableImage.get_key(image_id, tile_id)
            img_cache_val = self.image_cache_manager.get_cached(img_cache_key)
            mask_cache_key = CacheableMask.get_key(image_id, self.classid, tile_id)
            mask_cache_val = self.mask_cache_manager.get_cached(mask_cache_key)

            


            if img_cache_val:
                io_image = img_cache_val.get_image()
                x,y = img_cache_val.get_coordinates()
            else:

                io_image,x,y = load_tile(tile)

                
                try: #if memcache isn't working, no problem, just keep going
                    self.image_cache_manager.cache(img_cache_key, CacheableImage(io_image, (x, y)))
                except:
                    pass
            

            if mask_cache_val:
                mask_image, weight = mask_cache_val.get_mask(), mask_cache_val.get_weight()
            else:
                breakpoint()
                with get_session() as db_session: #TODO: Move down?
                    store = AnnotationStore(image_id, self.classid, is_gt=True, in_work_mag=True, mode=constants.AnnotationReturnMode.WKT)
                    annotations = store.get_annotations_for_tiles(tile_id)
                    db_session.expunge_all()

                    if len(annotations) == 0: # would be strange given how things are set up?
                        continue
            #----
                mask_image = np.zeros((self.tile_size, self.tile_size), dtype=np.uint8) #TODO: maybe should be moved to a project wide available utility function? not sure
                for annotation in annotations:
                    annotation_polygon = shapely.wkb.loads(annotation.polygon.data)
                    translated_polygon = shapely.affinity.translate(annotation_polygon, xoff=-x, yoff=-y) # need to scale this down from base mag to target mag
                    cv2.fillPoly(mask_image, [np.array(translated_polygon.exterior.coords, dtype=np.int32)], 1)
                
                
                mask_image = (mask_image>0).astype(np.uint8) # if two polygons slightly overlap, fillpoly is addiditve and you end upwith values >1
                
                if self.edge_weight:
                    weight = scipy.ndimage.morphology.binary_dilation(mask_image, iterations=2) & ~mask_image
                else:
                    weight = np.ones(mask_image.shape, dtype=mask_image.dtype)
                
                try: #if memcache isn't working, no problem, just keep going
                    # client.set(mask_cache_key, [compress_to_image_bytestream(i,format="PNG") for i in (mask_image, weight)])
                    self.mask_cache_manager.cache(mask_cache_key, CacheableMask(mask_image, weight))
                except:
                    pass

            img_new = io_image
            mask_new = mask_image
            weight_new = weight

            if self.transforms:
                augmented = self.transforms(image=io_image, masks=[mask_image, weight])
                img_new = augmented['image']
                mask_new, weight_new = augmented['masks']
            yield img_new, mask_new[None,::], weight_new