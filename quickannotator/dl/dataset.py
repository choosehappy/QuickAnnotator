import shapely.wkb
import numpy as np
import cv2
from sqlalchemy import Table, inspect, select, update, case, func
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model, load_tile
from quickannotator.db.models import Annotation, AnnotationClass, Image, Notification, Project, Setting, Tile
from torch.utils.data import IterableDataset

from quickannotator.db import get_session

from quickannotator.dl.utils import compress_to_jpeg, decompress_from_jpeg, get_memcached_client
from quickannotator.api.v1.tile.helper import tileid_to_point

from constants import TileStatus
import large_image
import numpy as np
from PIL import Image as PILImage
import scipy.ndimage
import cv2
import ray
import ray.train
import torch

class TileDataset(IterableDataset):
    def __init__(self, classid, tile_size,magnification,transforms=None, edge_weight=0, boost_count=5):
        self.classid = classid
        self.transforms = transforms
        self.edge_weight = edge_weight
        self.tile_size = tile_size
        self.magnification = magnification
        self.boost_count = boost_count
        
    def getWorkersTiles(self):
        with get_session() as db_session:  # Ensure this provides a session context
            with db_session.begin():  # Explicit transaction
                subquery = (
                    select(Tile.id)
                    .where(Tile.annotation_class_id == self.classid,
                        Tile.hasgt == True)
                    .order_by(Tile.gt_counter.asc(), Tile.gt_datetime.asc())  # Prioritize under-used, then newest
                    .limit(1).with_for_update(skip_locked=True) #with_for_update is a Postgres specific clause
                )
                

                tile = db_session.execute(
                    update(Tile)
                    .where(Tile.id == subquery.scalar_subquery())
                    .values(selection_count=(
                            # Only increment selection_count if it's less than max_selections
                            case(
                                (Tile.gt_counter < self.boost_count, Tile.gt_counter + 1),
                                else_=Tile.gt_counter
                            )
                        ),
                        gt_datetime=func.now())
                    .returning(Tile)
                ).scalar()
                
                return tile if tile else None
        

    def __iter__(self):
        client = get_memcached_client() ## client should be a "self" variable
        
        while tile:=self.getWorkersTiles():
            #print(tile)
            image_id = tile.image_id
            tile_id = tile.tile_id
            
            img_cache_key = f"img_{image_id}_{tile_id}"
            mask_cache_key = f"mask_{image_id}_{tile_id}"

            try: #if memcache isn't working, no problem, just keep going
                cache_vals = client.get_multi([img_cache_key, mask_cache_key]) or {}
            except:
                cache_vals = {}

            img_cache_val = cache_vals.get(img_cache_key,None)
            mask_cache_val = cache_vals.get(mask_cache_key,None)

            try:
                # if not inspector.has_table(table_name): #using a try catch to remove dependency on inspector
                #     continue
                table_name = build_annotation_table_name(image_id, self.classid, is_gt = True)
                table = create_dynamic_model(table_name)
                
            except:
                continue
            
            with get_session() as db_session: #TODO: Move down?
                annotations = db_session.query(table).filter(table.tile_id==tile_id).all()
                db_session.expunge_all()

            if len(annotations) == 0: # would be strange given how things are set up?
                continue
            #----

            if img_cache_val:
                io_image = decompress_from_jpeg(img_cache_val[0])
                x,y = img_cache_val[1]
            else:

                io_image,x,y = load_tile(tile)

                
                try: #if memcache isn't working, no problem, just keep going
                    client.set(img_cache_key, [compress_to_jpeg(io_image), (x,y)])
                except:
                    pass
            

            if mask_cache_val:
                mask_image, weight = [decompress_from_jpeg(i) for i in mask_cache_val]
            else:
                mask_image = np.zeros((self.tile_size, self.tile_size), dtype=np.uint8) #TODO: maybe should be moved to a project wide available utility function? not sure
                for annotation in annotations:
                    annotation_polygon = shapely.wkb.loads(annotation.polygon.data)
                    translated_polygon = shapely.affinity.translate(annotation_polygon, xoff=-x, yoff=-y) # need to scale this down from base mag to target mag
                    cv2.fillPoly(mask_image, [np.array(translated_polygon.exterior.coords, dtype=np.int32)], 1)
                if self.edge_weight:
                    weight = scipy.ndimage.morphology.binary_dilation(mask_image, iterations=2) & ~mask_image
                else:
                    weight = np.ones(mask_image.shape, dtype=mask_image.dtype)
                
                try: #if memcache isn't working, no problem, just keep going
                    client.set(mask_cache_key, [compress_to_jpeg(i) for i in (mask_image, weight)])
                except:
                    pass


            img_new = io_image
            mask_new = mask_image
            weight_new = weight
            #print("shapes!",img_new.shape, mask_new.shape, weight_new.shape)

            if self.transforms:
                augmented = self.transforms(image=io_image, masks=[mask_image, weight])
                img_new = augmented['image']
                mask_new, weight_new = augmented['masks']
            yield img_new, mask_new.unsqueeze(0), weight_new