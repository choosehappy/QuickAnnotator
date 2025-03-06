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
from sqlalchemy import Table, func, select, update
from quickannotator.constants import TileStatus
import ray
from quickannotator.db import get_session
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model, load_tile

            

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
        


def getPendingInferenceTiles(classid,batch_size_infer):
    with get_session() as db_session:  # Ensure this provides a session context
        with db_session.begin():  # Explicit transaction
            subquery = (
                select(Tile.id)
                .where(Tile.annotation_class_id == classid,
                    Tile.pred_status == TileStatus.STARTPROCESSING)
                .order_by(Tile.pred_datetime.desc()) #always get the latest ones first
                .limit(batch_size_infer).with_for_update(skip_locked=True) #with_for_update is a Postgres specific clause
            )

            tiles = db_session.execute(
                update(Tile)
                .where(Tile.id.in_(subquery))
                .where(Tile.pred_status == TileStatus.STARTPROCESSING)  # Ensures another worker hasn't claimed it
                .values(pred_status=TileStatus.PROCESSING,pred_datetime=func.now())
                .returning(Tile)
            ).scalars().all()
            
            return tiles if tiles else None

    
def update_tile_status(tile_batch,status):
    with get_session() as db_session:
        for tile in tile_batch:
            tile.pred_status = status
            tile.pred_datetime = func.now()
        db_session.bulk_save_objects(tile_batch)  # Bulk operation for efficiency
        db_session.commit()  # Commit changes

def run_inference(device, model, tiles):
    client = get_memcached_client()

    io_images = []
    infertiles = []
    for tile in tiles:
        img_cache_key = f"img_{tile.image_id}_{tile.id}" 
        try: #if memcache isn't working, no problem, just keep going
            img_cache_val = client.get(img_cache_key) or {}
        except:
            img_cache_val = {}
        
        if img_cache_val:
            io_image = decompress_from_jpeg(img_cache_val[0])

        else:
            io_image = load_tile(tile)

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
            save_annotations(tiles[j],polygons)

    update_tile_status(tiles, TileStatus.DONEPROCESSING) #now taht the batch is done, need to update tile status
    return outputs