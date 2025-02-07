from quickannotator.db.models import Annotation, AnnotationClass, Image, Notification, Project, Setting, Tile
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
from quickannotator.db import db, SearchCache
from quickannotator.dl.utils import compress_to_jpeg, decompress_from_jpeg, get_memcached_client
from quickannotator.dl.database import create_db_engine, get_database_path, get_session_aj
import cv2
from sqlalchemy import Table


def load_image_from_cache(cache_key): ## probably doesn't need to be a function...
    client = get_memcached_client() ## client should be a "self" variable
    cache_val = client.get(cache_key) ## COnsider here storing/retreiving images and masks seperately -- one can query multiple keys at the same time, so there isn't additional overhead but may make things more modular for future usage
    return cache_val
            


def load_image_from_slide(tile):
    session = get_session_aj(create_db_engine(get_database_path()))

    image = session.query(Image).filter_by(id=tile.image_id).first()
    image_path = image.path
    slide = openslide.OpenSlide("/opt/QuickAnnotator/quickannotator/"+image_path)

    tpoly = shapely.wkb.loads(tile.geom.data)
    minx, miny, maxx, maxy = tpoly.bounds #
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

def save_annotations(tile,polygons):
    gtpred = 'pred'
    table_name = f"{tile.image_id}_{tile.annotation_class_id}_{gtpred}_annotation"
    table = Table(table_name, db.metadata, autoload_with=create_db_engine(get_database_path()))
    
    tpoly = shapely.wkb.loads(tile.geom.data)
    minx, miny, maxx, maxy = tpoly.bounds

    new_annotations = []
    for polygon in polygons:
        translated_polygon = shapely.affinity.translate(polygon, xoff=minx, yoff=miny)
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
        print("new anno!\t\t:",new_annotation["image_id"],new_annotation["annotation_class_id"])
        new_annotations.append(new_annotation)
    #print(new_annotations)
    
    session = get_session_aj(create_db_engine(get_database_path()))
    session.execute(table.insert(), new_annotations)
    session.commit()


def getTileStatus(classid):
    import sqlalchemy, datetime
    from quickannotator.dl.database import create_db_engine, get_database_path, get_session_aj
    from quickannotator.db import db, SearchCache

    session = get_session_aj(create_db_engine(get_database_path()))
    stmt = session.query(Tile).filter(Tile.annotation_class_id == classid, Tile.seen == 1)
    
    result = stmt.all()
    
    session.close()

    return result


def batch_iterable(iterable, tile_batch_size):
    for i in range(0, len(iterable), tile_batch_size):
        yield iterable[i:i + tile_batch_size]

    
def update_tile_status(tile_batch):
    session = get_session_aj(create_db_engine(get_database_path())) #should have some error checking a context manager
    for tile in tile_batch:
        tile.seen = 2
    session.bulk_save_objects(tile_batch)  # Bulk operation for efficiency
    session.commit()  # Commit changes

def run_inference(model, tiles, device):
    session = get_session_aj(create_db_engine(get_database_path()))

    infer_tile_batch_size = 2  # need to get from project setting
    
    for tile_batch in batch_iterable(tiles, infer_tile_batch_size):
        io_images = []
        infertiles = []
        for tile in tile_batch:
            cache_key = f"{tile.image_id}_{tile.id}" ## This further suggests that we should be storing the IMAGE and the MASK seperately
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