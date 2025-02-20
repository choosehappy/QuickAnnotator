import shapely.wkb
import numpy as np
import cv2
from sqlalchemy import Table, inspect
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from quickannotator.db.models import Annotation, AnnotationClass, Image, Notification, Project, Setting, Tile
from torch.utils.data import IterableDataset

from quickannotator.db import get_session

from quickannotator.dl.utils import compress_to_jpeg, decompress_from_jpeg, get_memcached_client


import openslide
import numpy as np
from PIL import Image as PILImage
import scipy.ndimage
import cv2
import ray
import ray.train
import torch

class TileDataset(IterableDataset):
    def __init__(self, classid, tile_size,transforms=None, edge_weight=0):
        self.classid = classid
        self.transforms = transforms
        self.edge_weight = edge_weight
        self.tile_size = tile_size
        
        
    def getWorkersTiles(self):
        #note that we sort by reverse datetime - and then "pull out" alternating tiles based on worker ID
        #this in theory means if there are 6 new tiles, and 6 GPUs, each GPU will get one of the new tiles before moving to "less recent"
        with get_session() as db_session:


        #TODO: this should be generalized and refactoreed into a utility function - something
        #very similar is being done in inference.py getPendingInferenceTiles. the needed
        #function should take a list of tiles and return the ones that should be seen by the current worker
            tiles = db_session.query(Tile)\
                        .filter(Tile.annotation_class_id == self.classid, Tile.hasgt == True)\
                        .order_by(Tile.datetime.desc())\
                        .all()
            db_session.expunge_all()
        world_size= ray.train.get_context().get_world_size()
        world_rank= ray.train.get_context().get_world_rank()
        
        if world_size > 1: #filter down to entire list of tiles which should be seen by this GPU
            worker_tiles= [tile for idx, tile in enumerate(tiles) if idx % world_size == world_rank]
        else:
            worker_tiles = tiles

        pytorch_worker_info = torch.utils.data.get_worker_info()
        if pytorch_worker_info is None:  # single-process data loading, return the full iterator
            final_tiles= worker_tiles
        else: #further filter down to tiles which should be seen by *this* pytorch worker
            num_workers = pytorch_worker_info.num_workers
            worker_id = pytorch_worker_info.id
            final_tiles = [worker_tile for idx, worker_tile in enumerate(worker_tiles) if idx % num_workers == worker_id]

        return final_tiles
        

    def __iter__(self):
        client = get_memcached_client() ## client should be a "self" variable
        tiles = self.getWorkersTiles()
        
        for tile in tiles: #TODO: if this list is very long, and a new tile is added, it won't appear until the current queue is depleated
            image_id = tile.image_id
            tile_id = tile.tile_id
            
            img_cache_key = f"img_{image_id}_{tile_id}"
            mask_cache_key = f"mask_{image_id}_{tile_id}"
            cache_vals = client.get_multi([img_cache_key, mask_cache_key])
            img_cache_val = cache_vals.get(img_cache_key)
            mask_cache_val = cache_vals.get(mask_cache_key)

            try:
                # if not inspector.has_table(table_name): #using a try catch to remove dependency on inspector
                #     continue
                table_name = build_annotation_table_name(image_id, self.classid, is_gt = True)
                table = create_dynamic_model(table_name)
                
            except:
                continue
            
            with get_session() as db_session:
                annotations = db_session.query(table).filter(table.tile_id==tile_id).all()
                db_session.expunge_all()
                
            if len(annotations) == 0: # would be strange given how things are set up?
                continue
            #----

            if img_cache_val:
                io_image = decompress_from_jpeg(img_cache_val[0])
                row,col = img_cache_val[1]
            else:

                with get_session() as db_session:
                    image = db_session.query(Image).filter_by(id=image_id).first()
                    db_session.expunge_all()
                if not image:
                    continue
                image_path = image.path
                slide = openslide.OpenSlide("/opt/QuickAnnotator/quickannotator/"+image_path) #TODO: janky 


                #TODO: should be moved to a project wide available utility function
                tiles_per_row = np.ceil(image.width / self.tile_size) #width comes from DB
                row = tile_id // (tiles_per_row) * self.tile_size #seems right - but should check
                col = tile_id % (tiles_per_row) * self.tile_size

                region = slide.read_region((int(col), int(row)), 0, (self.tile_size, self.tile_size)) #note: row/col swap is intentional, read_region is  x,y
                io_image = np.array(region.convert("RGB"))
                client.set(img_cache_key, [compress_to_jpeg(io_image), (row,col)])
            

            if mask_cache_val:
                mask_image, weight = [decompress_from_jpeg(i) for i in mask_cache_val]
            else:
                mask_image = np.zeros((self.tile_size, self.tile_size), dtype=np.uint8) #TODO: maybe should be moved to a project wide available utility function? not sure
                for annotation in annotations:
                    annotation_polygon = shapely.wkb.loads(annotation.polygon.data)
                    translated_polygon = shapely.affinity.translate(annotation_polygon, xoff=-col, yoff=-row)
                    cv2.fillPoly(mask_image, [np.array(translated_polygon.exterior.coords, dtype=np.int32)], 1)
                if self.edge_weight:
                    weight = scipy.ndimage.morphology.binary_dilation(mask_image, iterations=2) & ~mask_image
                else:
                    weight = np.ones(mask_image.shape, dtype=mask_image.dtype)
                client.set(mask_cache_key, [compress_to_jpeg(i) for i in (mask_image, weight)])


            img_new = io_image
            mask_new = mask_image
            weight_new = weight
            if self.transforms:
                augmented = self.transforms(image=io_image, masks=[mask_image, weight])
                img_new = augmented['image']
                mask_new, weight_new = augmented['masks']
            yield img_new, mask_new.unsqueeze(0), weight_new