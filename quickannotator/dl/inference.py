import cv2

import torch
import numpy as np
import json
import shapely.wkb
import shapely.geometry
import shapely.affinity
import shapely.ops
import matplotlib.pyplot as plt
from sqlalchemy import func, select, text, update

from quickannotator.db.crud.annotation import AnnotationStore, build_annotation_table_name, table_exists
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor
from quickannotator.db.models import Tile
from quickannotator.db import get_session
from quickannotator.db import db_session as _db_session
from quickannotator.db.crud.tile import TileStoreFactory, TileStore

from quickannotator.constants import TileStatus
import quickannotator.constants as constants
from quickannotator.dl.utils import CacheableImage, load_tile, ImageCacheManager, contours_to_polygons
from quickannotator.db.fsmanager import fsmanager

from datetime import datetime
import logging
import os

logger = logging.getLogger(constants.LoggerNames.RAY.value)

# Cache of tissue-mask geometry per (image_id, annotation_class_id), expressed in the
# annotation class's working-magnification space so it can be compared directly with
# predicted polygons. Each entry carries a fingerprint of the image's Tissue Mask table and
# is rebuilt when that changes: the Ray actor is long-lived, and a cache that never
# refreshed kept clipping to the mask as it was when first read, so predictions on tissue
# added to the mask afterwards were all dropped.
_TISSUE_MASK_CACHE = {}


def _tissue_mask_fingerprint(image_id: int):
    """Cheap signature of the image's Tissue Mask annotations; None if there are none.

    Row count, newest id, total area and newest datetime change whenever a mask polygon is
    added, deleted or edited. One aggregate query (a few ms), run once per inference batch.
    """
    table = build_annotation_table_name(image_id, constants.MASK_CLASS_ID, is_gt=True)
    if not table_exists(table):
        return None
    # a plain read on the shared session, as AnnotationStore does below (get_session() would
    # commit and remove it as a side effect)
    row = _db_session.execute(
        text(f'SELECT count(*), max(id), sum(area), max(datetime) FROM "{table}"')).one()
    return None if row[0] == 0 else tuple(row)


def get_tissue_mask_geometry(image_id: int, annotation_class_id: int):
    """Union of the Tissue Mask annotations, in this class's working magnification.

    Tile gating is coarse: a tile is processed if ANY part of it touches tissue, so the
    model still runs over the blank portion of edge tiles (and, with MASK_DILATION, over
    whole blank tiles next to tissue). On background it tends to emit a confident,
    tile-shaped blob. Clipping predictions to the tissue mask removes those at source.

    Returns None if no mask exists, in which case predictions are left untouched.
    """
    key = (image_id, annotation_class_id)
    try:
        fingerprint = _tissue_mask_fingerprint(image_id)
    except Exception:
        logger.exception(f"Could not fingerprint the tissue mask of image {image_id}; reloading it.")
        fingerprint = object()          # never equal to a cached one: always rebuild
    cached = _TISSUE_MASK_CACHE.get(key)
    if cached is not None and cached[0] == fingerprint:
        return cached[1]
    if cached is not None:
        logger.info(f"Tissue mask of image {image_id} changed; reloading it for clipping.")

    geom = None
    try:
        store = AnnotationStore(image_id, constants.MASK_CLASS_ID, is_gt=True, in_work_mag=False)
        parts = []
        for ann in store.get_all_annotations():          # scaled to base magnification
            g = shapely.geometry.shape(json.loads(ann.polygon))
            if not g.is_valid:
                g = g.buffer(0)
            if not g.is_empty:
                parts.append(g)
        if parts:
            # base magnification -> this class's working magnification
            r = base_to_work_scaling_factor(image_id, annotation_class_id)
            union = shapely.ops.unary_union(parts)
            geom = shapely.affinity.scale(union, xfact=r, yfact=r, origin=(0, 0))
    except Exception:
        logger.exception(f"Could not build tissue mask for image {image_id}; "
                         f"predictions will not be clipped.")
        geom = None

    _TISSUE_MASK_CACHE[key] = (fingerprint, geom)
    return geom


def clip_polygons_to_tissue(polygons, image_id: int, annotation_class_id: int):
    """Drop predicted polygons that do not touch tissue, and trim those that straddle it."""
    mask = get_tissue_mask_geometry(image_id, annotation_class_id)
    if mask is None or not polygons:
        return polygons

    kept = []
    for poly in polygons:
        try:
            if not poly.intersects(mask):
                continue
            clipped = poly.intersection(mask)
            if clipped.is_empty:
                continue
            # intersection can yield a collection; keep the polygonal parts
            geoms = getattr(clipped, "geoms", [clipped])
            for g in geoms:
                if g.geom_type == "Polygon" and not g.is_empty and g.area > 0:
                    kept.append(g)
        except Exception:
            kept.append(poly)       # never lose a prediction to a geometry error
    return kept

def preprocess_image(io_image, device):
    """
    Preprocess image for inference: normalize to [0, 1], pad, and convert to tensor.
    
    Args:
        io_image: Input image as numpy array (H, W, C) in [0, 255] range
        device: PyTorch device to move tensor to
        
    Returns:
        Preprocessed image tensor of shape (1, 3, H+64, W+64)
    """
    io_image = io_image / 255.0  # Normalize to [0, 1]
    io_image = np.pad(io_image, ((32, 32), (32, 32), (0, 0)), mode='reflect')
    io_image = torch.tensor(io_image, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0).to(device)
    return io_image


def postprocess_output(outputs, min_area = 100, dilate_kernel = 2, inference_threshold: float = None):
    outputs = outputs.squeeze().detach().cpu().numpy()


    if constants.DEBUG:
        # Plot the output using matplotlib
        path = fsmanager.nas_write.get_debug_path()
        if not os.path.exists(path):
            os.makedirs(path)

        output_path = os.path.join(path, "output_plot.png")

        plt.figure(figsize=(10, 10))
        plt.imshow(outputs, cmap='viridis')  # Use 'viridis' colormap
        plt.colorbar(label='Output Intensity')  # Add a colorbar with a label
        plt.title('Model Output')
        plt.savefig(output_path)  # Save the plot as PNG
        plt.close()
        logger.debug(f"Saved output plot to {output_path}")  # Log the save location
        
    threshold = inference_threshold if inference_threshold is not None else constants.INFERENCE_THRESHOLD
    positive_mask = outputs > threshold
    
    kernel = np.ones((dilate_kernel, dilate_kernel), np.uint8)
    positive_mask = cv2.dilate(positive_mask.astype(np.uint8), kernel, iterations=2)>0

    contours, _ = cv2.findContours(positive_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    polygons = contours_to_polygons(contours, min_area=min_area)
    return polygons


def run_inference(device, model, tiles, inference_threshold: float = None):
    img_cache_manager = ImageCacheManager()

    io_images = []
    
    for tile in tiles:
        img_cache_val = img_cache_manager.get_cached(CacheableImage.get_key(tile.image_id, tile.annotation_class_id, tile.tile_id))
        
        if img_cache_val:
            io_image = img_cache_val.get_image()
            tile.x, tile.y = img_cache_val.get_coordinates()

        else:
            io_image,tile.x,tile.y = load_tile(tile)
            # NOTE: Should we also cache the image here? - Jackson - AJ: i don't think so, as the cache will rapidly be filled -- i would leave it only for DL based tiles

        if constants.DEBUG:
            path = fsmanager.nas_write.get_debug_path()
            if not os.path.exists(path):
                os.makedirs(path)
            io_image_path = os.path.join(path, f"tile_{tile.tile_id}_image.png")
            cv2.imwrite(io_image_path, io_image)  # Save the image for debugging
            logger.debug(f"Saved tile image to {io_image_path}")  # Log the save location

        io_images.append(io_image)

    io_images = [preprocess_image(io_image, device) for io_image in io_images]
    io_images = torch.cat(io_images, dim=0)
    logger.info(f"io_images going on GPU: \t {io_images.shape}")
    
    model.eval()
    with torch.no_grad():
        # Forward pass through multi-task model (returns dict with 'preds' and auxiliary outputs)
        model_output = model(io_images, return_recon=False, return_hv=False, return_obj_emb=False, return_pixel_emb=False)
        
        # Extract segmentation predictions and apply sigmoid
        preds = torch.sigmoid(model_output['preds'])
        
        # Remove padding applied during preprocessing
        preds = preds[:, :, 32:-32, 32:-32]

        for j, pred in enumerate(preds):
            #---
            # oo = pred.squeeze().detach().cpu().numpy()
            # cv2.imwrite("/opt/QuickAnnotator/output.png",oo) #TODO: remove- - for debug
            # np.save('/opt/QuickAnnotator/output.npy', oo)
            #---
            polygons = postprocess_output(pred, inference_threshold=inference_threshold) #some parmaeters here should be added to the class level config -- see function prototype
            translated_polygons = [
                shapely.affinity.translate(polygon, xoff=tiles[j].x, yoff=tiles[j].y) for polygon in polygons
            ]
            before_clip = len(translated_polygons)
            translated_polygons = clip_polygons_to_tissue(
                translated_polygons, tiles[j].image_id, tiles[j].annotation_class_id
            )
            if before_clip != len(translated_polygons):
                logger.info(f'Tissue clip on tile {tiles[j].tile_id}: '
                            f'{before_clip} -> {len(translated_polygons)} polygons.')
            logger.info(f'Saving annotations for tile {tiles[j].tile_id}.')
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
    return result #was pred - but we don't use this anyway - so might as well return the result of the upsert