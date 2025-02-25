from quickannotator.db.models import Annotation, AnnotationClass, Image, Notification, Project, Setting, Tile
import torch
import numpy as np
import shapely.wkb
import shapely.geometry
import shapely.affinity
import large_image
#import matplotlib.pyplot as plt
from sqlalchemy.orm import sessionmaker
from .dataset import TileDataset
from quickannotator.dl.utils import compress_to_jpeg, decompress_from_jpeg, get_memcached_client
import cv2, os
from sqlalchemy import Table, func
from quickannotator.constants import TileStatus
import ray
from quickannotator.db import get_session
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model



def load_image_from_cache(cache_key): ## probably doesn't need to be a function...
    client = get_memcached_client() ## client should be a "self" variable
    cache_val = client.get(cache_key) ## COnsider here storing/retreiving images and masks seperately -- one can query multiple keys at the same time, so there isn't additional overhead but may make things more modular for future usage
    return cache_val
            


def load_image_from_slide(tile): #TODO: i suspect this sort of function exists elsewhere within QA to serve tiles to the front end? change to merge functionality?
    with get_session() as db_session:
        image = db_session.query(Image).filter_by(id=tile.image_id).first()
    
    image_path = image.path
    
    ts = large_image.getTileSource(os.path.join("/opt/QuickAnnotator/quickannotator", image_path)) #TODO: JANKY

    tpoly = shapely.wkb.loads(tile.geom.data)
    minx, miny, maxx, maxy = tpoly.bounds #TODO: this seems incorrect - i feel like this information should be pulled from a system table and readily avaialble and not needing to be computed on a per tile basis
    width = int(maxx - minx)
    height = int(maxy - miny)

    #------------------ this is now sufficiently complex to be a function
    #region = slide.read_region((int(minx), int(miny)), 0, (width, height))
    region, _ = ts.getRegion(region=dict(left=minx, top=miny, width=width, height=height, units='base_pixels'),format=large_image.tilesource.TILE_FORMAT_NUMPY)
    image = region[:,:,:3]
    
    # Get actual height and width
    actual_height, actual_width, _ = io_image.shape

    # Compute padding amounts
    pad_height = max(0, self.tile_size - actual_height)
    pad_width = max(0, self.tile_size - actual_width)

    # Apply padding (black is default since mode='constant' and constant_values=0)
    io_image = np.pad(io_image, 
                    ((0, pad_height), (0, pad_width), (0, 0)), 
                    mode='constant', 
                    constant_values=0)

    #---------------

    return image #np.array(region.convert("RGB"))

def preprocess_image(io_image, device):
    io_image = io_image / 255.0
    io_image = (io_image - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
    io_image = np.pad(io_image, ((32, 32), (32, 32), (0, 0)), mode='reflect')
    io_image = torch.tensor(io_image, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0).to(device)
    return io_image

def postprocess_output(outputs, min_area = 100, dilate_kernel = 2): ## These should be defined as class level settings from the user
    outputs = outputs.squeeze().detach().cpu().numpy()
    positive_mask = outputs> 0
    
    kernel = np.ones((dilate_kernel, dilate_kernel), np.uint8)
    positive_mask = cv2.dilate(positive_mask.astype(np.uint8), kernel, iterations=2)>0

    contours, _ = cv2.findContours(positive_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    polygons = [shapely.geometry.Polygon(contour[:, 0, :]) for contour in contours if cv2.contourArea(contour) >= min_area]
    return polygons

def save_annotations(tile,polygons): #TODO: i feel like this function likely exists elsewhere in the system as well?
    table_name = build_annotation_table_name(tile.image_id, tile.annotation_class_id, is_gt = False)
    table = create_dynamic_model(table_name)
    
    tpoly = shapely.wkb.loads(tile.geom.data)
    minx, miny, maxx, maxy = tpoly.bounds

    new_annotations = []
    for polygon in polygons:
        translated_polygon = shapely.affinity.translate(polygon, xoff=minx, yoff=miny) #elegant
        area = translated_polygon.area
        centroid = translated_polygon.centroid
        
        new_annotation = {
            'image_id': tile.image_id,
            'annotation_class_id': tile.annotation_class_id,
            'polygon': translated_polygon.wkt,
            'area': area,
            'isgt': False,
            'centroid': centroid.wkt
        }
        print("new anno!\t\t:",new_annotation["image_id"],new_annotation["annotation_class_id"]) #TODO: push to logging or remove
        new_annotations.append(new_annotation)
    #print(new_annotations)
    
    with get_session() as db_session:
        db_session.execute(table.insert(), new_annotations)
        


def getPendingInferenceTiles(classid):
    with get_session() as db_session:
        tiles = db_session.query(Tile)\
                        .filter(Tile.annotation_class_id == classid, Tile.seen == TileStatus.STARTPROCESSING)\
                        .order_by(Tile.datetime.desc())\
                        .all() 
    
    update_tile_status(tiles,TileStatus.PROCESSING)

    #TODO: turn into util function with data loader, for distirubting tile to workers
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


def batch_iterable(iterable, tile_batch_size): #TODO: check version of python in container -- a function like this is avaialble  in itertools and should be used instead
    #needs python 3.12
    for i in range(0, len(iterable), tile_batch_size):
        yield iterable[i:i + tile_batch_size]

    
def update_tile_status(tile_batch,status):
    with get_session() as db_session:
        for tile in tile_batch:
            tile.seen = status
            tile.datetime = func.now()
        db_session.bulk_save_objects(tile_batch)  # Bulk operation for efficiency
        db_session.commit()  # Commit changes

def run_inference(model, tiles, device):
    infer_tile_batch_size = 2  #TODO: need to get from project setting
    
    for tile_batch in batch_iterable(tiles, infer_tile_batch_size):
        io_images = []
        infertiles = []
        for tile in tile_batch:
            cache_key = f"{tile.image_id}_{tile.id}" ##TODO: This further suggests that we should be storing the IMAGE and the MASK seperately
            cache_val = load_image_from_cache(cache_key)
            if cache_val:
                io_image, mask_image, weight = [decompress_from_jpeg(i) for i in cache_val]
            else:
                io_image = load_image_from_slide(tile) #TODO: Util function with large_image
            io_images.append(io_image)

        io_images = [preprocess_image(io_image, device) for io_image in io_images]
        io_images = torch.cat(io_images, dim=0)
        print(f"io_images going on GPU: \t {io_images.shape}")
        
        model.eval()
        with torch.no_grad():
            outputs = model(io_images)  #output at target magnification level!
            outputs = outputs[:, :, 32:-32, 32:-32]

            for j, output in enumerate(outputs):
                polygons = postprocess_output(output) #some parmaeters here should be added to the class level config -- see function prototype
                #TODO: !!!! need to upscale polygons to base magnification size
                save_annotations(tile_batch[j],polygons)

        update_tile_status(tile_batch, TileStatus.DONEPROCESSING) #now taht the batch is done, need to update tile status
    return outputs