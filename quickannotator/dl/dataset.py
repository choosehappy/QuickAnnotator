import shapely.wkb
import cv2, numpy as np

import scipy.ndimage
from torch.utils.data import IterableDataset

from sqlalchemy import  select, update, case, func

from quickannotator.db import get_session
from quickannotator.db.models import Tile
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from quickannotator.db.annotation_class_crud import get_annotation_class_by_id
from datetime import datetime


from quickannotator.dl.utils import compress_to_image_bytestream, decompress_from_image_bytestream, get_memcached_client, load_tile 

class TileDataset(IterableDataset):
    def __init__(self, classid, transforms=None, edge_weight=0, boost_count=5):
        self.classid = classid
        self.transforms = transforms
        self.edge_weight = edge_weight
        self.boost_count = boost_count
        with get_session() as db_session:  # Ensure this provides a session context
            annotation_class = get_annotation_class_by_id(classid)
            self.magnification = annotation_class.work_mag
            self.tile_size = annotation_class.work_tilesize
        
    def getWorkersTiles(self) -> Tile | None:
        with get_session() as db_session:  # Ensure this provides a session context
            subquery = (
                select(Tile.id)
                .where(Tile.annotation_class_id == self.classid,
                    Tile.gt_datetime.isnot(None))
                .order_by(Tile.gt_counter.asc(), Tile.gt_datetime.asc())  # Prioritize under-used, then newest
                .limit(1).with_for_update(skip_locked=True) #with_for_update is a Postgres specific clause
            )
                
            with db_session.begin():  # Explicit transaction

                tile = db_session.execute(
                    update(Tile)
                    .where(Tile.id == subquery.scalar_subquery())
                    .values(gt_counter=(
                            # Only increment selection_count if it's less than max_selections
                            case(
                                (Tile.gt_counter < self.boost_count, Tile.gt_counter + 1),
                                else_=Tile.gt_counter
                            )
                        ),
                        gt_datetime=datetime.now())
                    .returning(Tile)
                ).scalar()
                db_session.expunge(tile)
            
            #print(f"tile retval {tile}")
            return tile if tile else None
        

    def __iter__(self):
        client = get_memcached_client() ## client should be a "self" variable
        
        while tile:=self.getWorkersTiles():
            #print(tile)
            #print(f"tile retval 2 {tile}")

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
                io_image = decompress_from_image_bytestream(img_cache_val[0])
                x,y = img_cache_val[1]
            else:

                io_image,x,y = load_tile(tile)

                
                try: #if memcache isn't working, no problem, just keep going
                    client.set(img_cache_key, [compress_to_image_bytestream(io_image,format="JPEG", quality=95), (x,y)])
                except:
                    pass
            

            if mask_cache_val:
                mask_image, weight = [decompress_from_image_bytestream(i) for i in mask_cache_val]
            else:
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
                    client.set(mask_cache_key, [compress_to_image_bytestream(i,format="PNG") for i in (mask_image, weight)])
                except:
                    pass

            # cv2.imwrite(f"/opt/QuickAnnotator/{tile_id}_mask.png",mask_image*255) #TODO: remove- - for debug
            # cv2.imwrite(f"/opt/QuickAnnotator/{tile_id}_img.png",io_image)#TODO: remove- - for debug
            # cv2.imwrite(f"/opt/QuickAnnotator/{tile_id}_weight_2.png",weight*255)#TODO: remove- - for debug
            img_new = io_image
            mask_new = mask_image
            weight_new = weight
            #print("shapes!",img_new.shape, mask_new.shape, weight_new.shape)

            if self.transforms:
                augmented = self.transforms(image=io_image, masks=[mask_image, weight])
                img_new = augmented['image']
                mask_new, weight_new = augmented['masks']
            yield img_new, mask_new[None,::], weight_new