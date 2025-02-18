import torch
import numpy as np
import shapely.wkb
import shapely.geometry
import shapely.affinity
import openslide
#import matplotlib.pyplot as plt
from sqlalchemy.orm import sessionmaker
from .dataset import TileDataset
from .database import db
from quickannotator.db import db, Project, Image, AnnotationClass, Notification, Tile, Setting, Annotation
from quickannotator.dl.utils import compress_to_jpeg, decompress_from_jpeg, get_memcached_client
from quickannotator.dl.database import create_db_engine, get_database_path, get_session_aj
import cv2, os
from sqlalchemy import Table
import ray

def load_image_from_cache(cache_key): ## probably doesn't need to be a function...
    client = get_memcached_client() ## client should be a "self" variable
    cache_val = client.get(cache_key) ## COnsider here storing/retreiving images and masks seperately -- one can query multiple keys at the same time, so there isn't additional overhead but may make things more modular for future usage
    return cache_val
            


def load_image_from_slide(tile): #TODO: i suspect this sort of function exists elsewhere within QA to serve tiles to the front end? change to merge functionality?
    session = get_session_aj(create_db_engine(get_database_path()))

    image = session.query(Image).filter_by(id=tile.image_id).first()
    image_path = image.path
    slide = openslide.OpenSlide(os.path.join("/opt/QuickAnnotator/quickannotator", image_path))

    tpoly = shapely.wkb.loads(tile.geom.data)
    minx, miny, maxx, maxy = tpoly.bounds #TODO: this seems incorrect - i feel like this information should be pulled from a system table and readily avaialble and not needing to be computed on a per tile basis
    width = int(maxx - minx)
    height = int(maxy - miny)

    region = slide.read_region((int(minx), int(miny)), 0, (width, height))
    return np.array(region.convert("RGB"))

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
    gtpred = 'pred'
    table_name = f"{tile.image_id}_{tile.annotation_class_id}_{gtpred}_annotation"
    table = Table(table_name, db.metadata, autoload_with=create_db_engine(get_database_path()))
    
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
    
    session = get_session_aj(create_db_engine(get_database_path()))
    session.execute(table.insert(), new_annotations)
    session.commit()


def getPendingInferenceTiles(classid):
    import sqlalchemy, datetime #gross - but i'm afraid of removing and breaeking something :)
    from quickannotator.dl.database import create_db_engine, get_database_path, get_session_aj
    from quickannotator.db import db, Project, Image, AnnotationClass, Notification, Tile, Setting, Annotation

    with get_session_aj(create_db_engine(get_database_path())) as session:
    
    
        tiles = session.query(Tile)\
                        .filter(Tile.annotation_class_id == classid, Tile.seen == 1)\
                        .order_by(Tile.datetime.desc())\
                        .all() 
    
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

    
def update_tile_status(tile_batch):
    session = get_session_aj(create_db_engine(get_database_path())) #should have some error checking a context manager
    for tile in tile_batch:
        tile.seen = 2 #TODO: replace with named enum
    session.bulk_save_objects(tile_batch)  # Bulk operation for efficiency
    session.commit()  # Commit changes

def run_inference(model, tiles, device):
    session = get_session_aj(create_db_engine(get_database_path()))

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
                io_image = load_image_from_slide(tile)
            io_images.append(io_image)

        io_images = [preprocess_image(io_image, device) for io_image in io_images]
        io_images = torch.cat(io_images, dim=0)
        print(f"io_images going on GPU: \t {io_images.shape}")
        
        model.eval()
        with torch.no_grad():
            outputs = model(io_images)
            outputs = outputs[:, :, 32:-32, 32:-32]

            for j, output in enumerate(outputs):
                polygons = postprocess_output(output) #some parmaeters here should be added to the class level config -- see function prototype
                save_annotations(tile_batch[j],polygons)

        update_tile_status(tile_batch) #now taht the batch is done, need to set seen = 2
    session.close()
    return outputs