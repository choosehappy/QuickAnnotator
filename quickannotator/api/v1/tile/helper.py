import quickannotator.db as qadb
from sqlalchemy import func, Table
from quickannotator.db import db_session
from sqlalchemy import exists, event
import shapely
from shapely.affinity import scale
from shapely.geometry import Polygon
import shapely.wkb as wkb
import random
import geojson
from quickannotator.api.v1.utils.shared_crud import insert_new_annotation, get_tile
from multiprocessing import Process, current_process
import time
import ray
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import math
import numpy as np
from sqlalchemy.dialects.sqlite import insert   # NOTE: This import is necessary as there is no dialect-neutral way to call on_conflict()
from quickannotator.api.v1.utils.shared_crud import get_annotation_query
import quickannotator.db.models as models
from quickannotator.db import get_session
from quickannotator.api.v1.image.utils import get_image_by_id
from quickannotator.api.v1.annotation_class.helper import get_annotation_class_by_id
import cv2
from quickannotator.constants import TileStatus

from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model

def upsert_tile(annotation_class_id: int, image_id: int, tile_id: int, seen: TileStatus=None, hasgt: bool=None):
    '''
        Inserts a new tile record into the database or updates an existing one based on the given parameters.
        The function uses an upsert operation to either insert a new record or update an existing one
        based on the combination of `annotation_class_id`, `image_id`, and `tile_id`.
        Parameters:
        - annotation_class_id (int): The ID of the annotation class.
        - image_id (int): The ID of the image.
        - tile_id (int): The ID of the tile.
        - seen (int): The seen status of the tile.
        - hasgt (bool): A flag indicating whether the tile is ground truth (True) or not (False).
        Returns:
        - result: The result of the executed statement.
    '''
    update_fields = {}
    if seen is not None:    # Only update the 'seen' field if the value is provided
        update_fields['seen'] = seen
    if hasgt is not None:   # Only update the 'hasgt' field if the value is provided
        update_fields['hasgt'] = hasgt
    
    stmt = insert(models.Tile).values(
        annotation_class_id=annotation_class_id,
        image_id=image_id,
        tile_id=tile_id,
        **update_fields
    ).on_conflict_do_update(
        index_elements=['annotation_class_id', 'image_id', 'tile_id'],
        set_=update_fields
    )
    
    result = db_session.execute(stmt)
    db_session.commit()
    
    return result
    

def get_tile_ids_within_bbox(tile_size: int, image_width: int, image_height: int, bbox: list[int]) -> list:
    # Force the bounding box to be within the image dimensions for robustness.
    x1 = max(0, min(bbox[0], image_width))
    y1 = max(0, min(bbox[1], image_height))
    x2 = max(0, min(bbox[2], image_width))
    y2 = max(0, min(bbox[3], image_height))

    # Verify that the bounding box is within the image dimensions
    if not (x1 < x2 and y1 < y2):
        raise ValueError(f"Bounding box coordinates must be monotonically increasing: {bbox}")

    # Calculate the number of tiles per row
    tiles_per_row = math.ceil(image_width / tile_size)

    # Determine the tile range
    start_col = x1 // tile_size
    end_col = math.ceil(x2 / tile_size) - 1
    start_row = y1 // tile_size
    end_row = math.ceil(y2 / tile_size) - 1
    
    # Create a mesh grid of tile coordinates
    cols, rows = np.meshgrid(np.arange(start_col, end_col + 1), np.arange(start_row, end_row + 1))

    # Flatten the mesh grid and calculate tile IDs
    tile_ids = (rows * tiles_per_row + cols).flatten().tolist()

    return tile_ids

def point_to_tileid(tile_size: int, image_width: int, image_height: int, x: int, y: int) -> int:
    if not (0 <= x < image_width and 0 <= y < image_height):
        raise ValueError(f"Point {x}, {y} is out of image dimensions (0, 0, {image_width}, {image_height})")

    col = x // tile_size
    row = y // tile_size
    tile_id = rc_to_tileid(tile_size, image_width, image_height, row, col)
    return tile_id

def rc_to_tileid(tile_size: int, image_width: int, image_height: int, row: int, col: int) -> int:
    tile_id = row * math.ceil(image_width / tile_size) + col
    return tile_id

def tileid_to_rc(tile_size: int, image_width: int, image_height: int, tile_id: int) -> tuple:
    tiles_per_row = math.ceil(image_width / tile_size)
    row = tile_id // tiles_per_row
    col = tile_id % tiles_per_row
    return (row, col)

def get_all_tile_ids_for_image(tile_size: int, image_width: int, image_height: int) -> list:
    total_tiles = math.ceil(image_width / tile_size) * math.ceil(image_height / tile_size)
    return list(range(total_tiles))

def get_bbox_for_tile(tile_size: int, image_width: int, image_height: int, tile_id: int) -> tuple:
    row, col = tileid_to_rc(tile_size, image_width, image_height, tile_id)

    x1 = col * tile_size
    y1 = row * tile_size
    x2 = x1 + tile_size
    y2 = y1 + tile_size

    return (x1, y1, x2, y2)

def tile_intersects_mask_shapely(image_id: int, annotatation_class_id: int, tile_id: int) -> bool:
    image = get_image_by_id(image_id)
    tilesize = get_annotation_class_by_id(annotatation_class_id).tilesize

    bbox = get_bbox_for_tile(tilesize, image.width, image.height, tile_id)
    model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id=1, is_gt=True))
    mask_annotations = db_session.query(model).all()

    if mask_annotations:
        bbox_polygon = Polygon([(bbox[0], bbox[1]), (bbox[2], bbox[1]), (bbox[2], bbox[3]), (bbox[0], bbox[3])])
        for ann in mask_annotations:
            if bbox_polygon.intersects(wkb.loads(ann.polygon.data)):
                return True
    
    return False

def tile_intersects_mask(image_id: int, annotation_class_id: int, tile_id: int) -> bool:
    tileids, _, _ = get_tile_ids_intersecting_mask(image_id, annotation_class_id, mask_dilation=1)
    return tile_id in set(tileids)

def get_tile_ids_intersecting_mask(image_id: int, annotation_class_id: int, mask_dilation: int) -> tuple[list, np.ndarray, list]:
    image = get_image_by_id(image_id)
    tilesize = get_annotation_class_by_id(annotation_class_id).tilesize
    
    # Load GeoJSON mask (assuming polygon)
    model = create_dynamic_model(build_annotation_table_name(image_id, 1, is_gt=True))
    mask_geojson = get_annotation_query(model).all()

    polygons = []

    scale_factor = 1/tilesize
    for annotation in mask_geojson:
        shapely_polygon = shapely.from_geojson(annotation.polygon)
        scaled_polygon = scale(shapely_polygon, xfact=scale_factor, yfact=scale_factor, origin=(0, 0))
        polygons.append(np.floor(scaled_polygon.exterior.coords).astype(np.int32))


    # Create empty mask image
    mask_shape = np.ceil(np.array([image.height, image.width]) / tilesize).astype(np.int32)
    mask = np.zeros(mask_shape, dtype=np.uint8)
    
    # Draw filled mask
    cv2.fillPoly(mask, polygons, 255, lineType=cv2.LINE_4)
    
    # Dilate mask
    # kernel = np.ones((3, 3), np.uint8)
    kernel = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=mask_dilation)

    # Get non-zero (filled) pixels
    filled_rows, filled_cols = np.nonzero(mask)
    
    # Convert pixel coordinates to tile IDs
    tile_ids = [rc_to_tileid(tilesize, image.width, image.height, row, col) for row, col in zip(filled_rows, filled_cols)]

    return tile_ids, mask, polygons


def generate_random_circle_within_bbox(bbox: Polygon, radius: float) -> shapely.geometry.Polygon:
    minx, miny, maxx, maxy = bbox.bounds
    x = minx + (maxx - minx) * random.random()
    y = miny + (maxy - miny) * random.random()

    circle = shapely.geometry.Point(x, y).buffer(radius)
    intersection = bbox.intersection(circle)
    return intersection

@ray.remote
def remote_compute_on_tile(annotation_class_id: int, image_id: int, tile_id: int, sleep_time=5):
    time.sleep(sleep_time)
    # Create the engine and session for each Ray task
        # Start a session for the task
    with get_session() as db_session:
        # Example: load the tile and process
        # breakpoint()
        tile = get_tile(annotation_class_id, image_id, tile_id)  # Replace with your actual function to get the tile
        if tile is None:
            raise ValueError(f"Tile not found: {tile_id}")
        annotation_class: models.AnnotationClass = tile.annotation_class
        image: models.Image = tile.image
        image_id: int = tile.image_id
        annotation_class_id: int = tile.annotation_class_id

        # Process the tile (using shapely for example)
        bbox = get_bbox_for_tile(annotation_class.tilesize, image.width, image.height, tile_id)
        bbox_polygon = Polygon([(bbox[0], bbox[1]), (bbox[2], bbox[1]), (bbox[2], bbox[3]), (bbox[0], bbox[3])])
        for _ in range(random.randint(20, 40)):
            polygon = generate_random_circle_within_bbox(bbox_polygon, 100)
            insert_new_annotation(image_id, annotation_class_id, is_gt=False, tile_id=tile_id, polygon=polygon)

        # Mark tile as processed
        tile.seen = 2
            



def compute_on_tile(annotation_class_id: int, image_id: int, tile_id: int, sleep_time=5):
    ref = remote_compute_on_tile.remote(annotation_class_id, image_id, tile_id, sleep_time)
    return ref.hex()


def reset_all_tiles_seen():
    """
    Resets the 'seen' status of all tiles in the database to 0.
    Args:
        db: The database session object used to interact with the database.
    Returns:
        None
    """

    db_session.query(models.Tile).update({models.Tile.seen: TileStatus.UNSEEN})