from quickannotator.db import db_session
import shapely
from shapely.affinity import scale
from shapely.geometry import Polygon, shape
import shapely.wkb as wkb
import random
import time
import ray
import numpy as np
import cv2
import geojson

from quickannotator.api.v1.utils.shared_crud import get_annotation_query
import quickannotator.db.models as models
from quickannotator.db import get_session
from quickannotator.api.v1.image.utils import get_image_by_id
from quickannotator.db.crud.annotation_class import get_annotation_class_by_id
from quickannotator.api.v1.utils.shared_crud import get_tile
from quickannotator.api.v1.utils.coordinate_space import get_tilespace
from quickannotator.constants import TileStatus, MASK_CLASS_ID, MASK_DILATION
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor

# TODO: DEPRECATED Remove this method as it is not used.
def tile_intersects_mask_shapely(image_id: int, annotatation_class_id: int, tile_id: int) -> bool:

    bbox = get_tilespace(image_id=image_id, annotation_class_id=annotatation_class_id).get_bbox_for_tile(tile_id)
    model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id=1, is_gt=True))
    mask_annotations = get_annotation_query(model).all()

    if mask_annotations:
        bbox_polygon = Polygon([(bbox[0], bbox[1]), (bbox[2], bbox[1]), (bbox[2], bbox[3]), (bbox[0], bbox[3])])
        for ann in mask_annotations:
            if bbox_polygon.intersects(wkb.loads(ann.polygon.data)):
                return True
    
    return False

def tile_intersects_mask(image_id: int, annotation_class_id: int, tile_id: int) -> bool:
    tileids, _, _ = get_tile_ids_intersecting_mask(image_id, annotation_class_id, mask_dilation=MASK_DILATION)
    return tile_id in set(tileids)

def get_tile_ids_intersecting_mask(image_id: int, annotation_class_id: int, mask_dilation: int) -> tuple[list, np.ndarray, list]:
    # This function operates in the base magnification space
    mask_work_to_base_scale_factor = 1 / base_to_work_scaling_factor(image_id=image_id, annotation_class_id=MASK_CLASS_ID)
    
    # Get the mask geojson polygons
    model = create_dynamic_model(build_annotation_table_name(image_id, MASK_CLASS_ID, is_gt=True))
    mask_geojson: geojson.Polygon = [geojson.loads(ann.polygon) for ann in get_annotation_query(model, mask_work_to_base_scale_factor).all()]    # Scales mask to base mag

    tile_ids, mask, processed_polygons = get_tile_ids_intersecting_polygons(image_id, annotation_class_id, mask_geojson, mask_dilation)

    return tile_ids, mask, processed_polygons

def get_tile_ids_intersecting_polygons(image_id: int, annotation_class_id: int, base_polygons: list[geojson.Polygon], mask_dilation: int):
    """
    Get tile IDs that intersect with given polygons for a specific image and annotation class.
    Args:
        image_id (int): The ID of the image.
        annotation_class_id (int): The ID of the annotation class.
        base_polygons (list[geojson.Polygon]): A list of polygons in GeoJSON format. These polygons should be in the base magnification space.
        mask_dilation (int): The number of iterations for mask dilation.
    Returns:
        tuple: A tuple containing:
            - tile_ids (list[int]): A list of tile IDs that intersect with the polygons.
            - mask (np.ndarray): The binary mask image with filled polygons.
            - processed_polygons (list[np.ndarray]): A list of processed polygons with scaled coordinates.
    """

    image = get_image_by_id(image_id)
    base_tilesize = get_annotation_class_by_id(annotation_class_id).work_tilesize / base_to_work_scaling_factor(image_id=image_id, annotation_class_id=annotation_class_id)
    processed_polygons = []
    scale_factor = 1 / base_tilesize
    for polygon in base_polygons:
        shapely_polygon = shape(polygon)
        scaled_polygon = scale(shapely_polygon, xfact=scale_factor, yfact=scale_factor, origin=(0, 0))
        processed_polygons.append(np.floor(scaled_polygon.exterior.coords).astype(np.int32))

    # Create empty mask image
    mask_shape = np.ceil(np.array([image.base_height, image.base_width]) / base_tilesize).astype(np.int32)
    mask = np.zeros(mask_shape, dtype=np.uint8)
    
    # Draw filled mask
    cv2.fillPoly(mask, processed_polygons, 255, lineType=cv2.LINE_4)
    
    # Dilate mask
    kernel = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=mask_dilation)

    # Get non-zero (filled) pixels
    filled_rows, filled_cols = np.nonzero(mask)

    tilespace = get_tilespace(image_id=image_id, annotation_class_id=annotation_class_id, in_work_mag=False)
    
    # Convert pixel coordinates to tile IDs
    tile_ids = [tilespace.rc_to_tileid(row, col) for row, col in zip(filled_rows.tolist(), filled_cols.tolist())]

    return tile_ids, mask, processed_polygons

def generate_random_circle_within_bbox(bbox: Polygon, radius: float) -> shapely.geometry.Polygon:
    minx, miny, maxx, maxy = bbox.bounds
    x = minx + (maxx - minx) * random.random()
    y = miny + (maxy - miny) * random.random()

    circle = shapely.geometry.Point(x, y).buffer(radius)
    intersection = bbox.intersection(circle)
    return intersection

def get_tiles_by_tile_ids(image_id: int, annotation_class_id: int, tile_ids: list[int], hasgt=False) -> list[models.Tile]:
    """
    Get tiles by their IDs.
    
    Args:
        image_id (int): The ID of the image.
        annotation_class_id (int): The ID of the annotation class.
        tile_ids (list[int]): A list of tile IDs.
        hasgt (bool): Flag to filter tiles that have ground truth annotations.
        
    Returns:
        list[models.Tile]: A list of tile objects.
    """
    query = db_session.query(models.Tile).filter(
        models.Tile.image_id == image_id,
        models.Tile.annotation_class_id == annotation_class_id,
        models.Tile.tile_id.in_(tile_ids)
    )
    
    if hasgt:
        query = query.filter(models.Tile.gt_datetime.isnot(None))
    
    return query.all()
