import cv2

import torch
import numpy as np
import shapely.wkb
import shapely.geometry
import shapely.affinity

from sqlalchemy import func, select, update

from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.models import Tile
from quickannotator.db import get_session
from quickannotator.db.crud.tile import TileStoreFactory, TileStore

from quickannotator.constants import TileStatus
import quickannotator.constants as constants
from quickannotator.dl.utils import CacheableImage, load_tile, ImageCacheManager

from datetime import datetime
import logging

logger = logging.getLogger(constants.LoggerNames.RAY.value)

def preprocess_image(io_image, device):
    io_image = io_image / 255.0
    io_image = (io_image - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
    io_image = np.pad(io_image, ((32, 32), (32, 32), (0, 0)), mode='reflect')
    io_image = torch.tensor(io_image, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0).to(device)
    return io_image


def postprocess_output(outputs, min_area = 100, dilate_kernel = 2): ## These should be defined as class level settings from the user
    outputs = outputs.squeeze().detach().cpu().numpy()
    positive_mask = outputs> .5 #TODO: maybe UI or system threshold? probably a good idea
    
    kernel = np.ones((dilate_kernel, dilate_kernel), np.uint8)
    positive_mask = cv2.dilate(positive_mask.astype(np.uint8), kernel, iterations=2)>0

    contours, _ = cv2.findContours(positive_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    polygons = [shapely.geometry.Polygon(contour[:, 0, :]) for contour in contours if cv2.contourArea(contour) >= min_area]
    return polygons


def run_inference(device, model, tiles):
    img_cache_manager = ImageCacheManager()

    io_images = []
    
    for tile in tiles:
        img_cache_val = img_cache_manager.get_cached(CacheableImage.get_key(tile.image_id, tile.tile_id))
        
        if img_cache_val:
            io_image = img_cache_val.get_image()
            tile.x, tile.y = img_cache_val.get_coordinates()

        else:
            io_image,tile.x,tile.y = load_tile(tile)
            # NOTE: Should we also cache the image here? - Jackson

        cv2.imwrite("/opt/QuickAnnotator/quickannotator/data/output/img.png",io_image) #TODO: remove- - for debug
        io_images.append(io_image)

    io_images = [preprocess_image(io_image, device) for io_image in io_images]
    io_images = torch.cat(io_images, dim=0)
    logger.info(f"io_images going on GPU: \t {io_images.shape}")
    
    model.eval()
    with torch.no_grad():
        outputs = model(io_images)  #output at target magnification level!
        outputs = torch.sigmoid(outputs) #BCEWithLogitsLoss needs a sigmoid at the end
        outputs = outputs[:, :, 32:-32, 32:-32]

        for j, output in enumerate(outputs):
            #---
            # oo = outputs.squeeze().detach().cpu().numpy()
            # cv2.imwrite("/opt/QuickAnnotator/output.png",oo) #TODO: remove- - for debug
            # np.save('/opt/QuickAnnotator/output.npy', oo)
            #---
            polygons = postprocess_output(output) #some parmaeters here should be added to the class level config -- see function prototype
            translated_polygons = [
                shapely.affinity.translate(polygon, xoff=tiles[j].x, yoff=tiles[j].y) for polygon in polygons
            ]
            logger.info(f'Saving annotations for tile {tiles[j].id}.')
            with get_session() as db_session:
                store = AnnotationStore(tiles[j].image_id, tiles[j].annotation_class_id, is_gt=False, in_work_mag=True)
                store.delete_annotations_by_tile(tiles[j].tile_id)
                store.insert_annotations(translated_polygons, tiles[j].tile_id)

            logger.info(f'Number of annotations saved: {len(translated_polygons)}.')
                
    logger.info("Setting pred_status to DONEPROCESSING")
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    result = tilestore.upsert_pred_tiles(image_id=tiles[0].image_id, 
                      annotation_class_id=tiles[0].annotation_class_id, 
                      tile_ids={tile.tile_id for tile in tiles}, 
                      pred_status=TileStatus.DONEPROCESSING, 
                      process_owns_tile=True)
    return outputs