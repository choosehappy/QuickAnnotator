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
    

class TileSpace:
    def __init__(self, work_tilesize: int, image_width_at_work_mag: int, image_height_at_work_mag: int):
        self.ts = work_tilesize
        self.w = image_width_at_work_mag
        self.h = image_height_at_work_mag

    def get_tile_ids_within_bbox(self, bbox: list[int]) -> list:
        """
        Get the tile IDs within a specified bounding box.
        This method calculates the tile IDs that fall within the given bounding box
        coordinates. The bounding box coordinates are adjusted to ensure they are
        within the image dimensions.
        Args:
            bbox (list[int]): A list of four integers representing the bounding box
                              coordinates [x1, y1, x2, y2]. Each coordinate must be in the working magnification space.
        Returns:
            list: A list of tile IDs that fall within the specified bounding box.
        Raises:
            ValueError: If the bounding box coordinates are not monotonically increasing.
        """

        # Force the bounding box to be within the image dimensions for robustness.
        x1 = max(0, min(bbox[0], self.w))
        y1 = max(0, min(bbox[1], self.h))
        x2 = max(0, min(bbox[2], self.w))
        y2 = max(0, min(bbox[3], self.h))

        # Verify that the bounding box is within the image dimensions
        if not (x1 < x2 and y1 < y2):
            raise ValueError(f"Bounding box coordinates must be monotonically increasing: {bbox}")

        # Calculate the number of tiles per row
        tiles_per_row = math.ceil(self.w / self.ts)

        # Determine the tile range
        start_col = x1 // self.ts
        end_col = math.ceil(x2 / self.ts) - 1
        start_row = y1 // self.ts
        end_row = math.ceil(y2 / self.ts) - 1
        
        # Create a mesh grid of tile coordinates
        cols, rows = np.meshgrid(np.arange(start_col, end_col + 1), np.arange(start_row, end_row + 1))

        # Flatten the mesh grid and calculate tile IDs
        tile_ids = (rows * tiles_per_row + cols).flatten().tolist()

        return tile_ids

    def point_to_tileid(self, x: int, y: int) -> int:
        """
        Convert a point (x, y) to a tile ID.
        Args:
            x (int): The x-coordinate of the point.in the workmag space.
            y (int): The y-coordinate of the point.in the workmag space.
        Returns:
            int: The tile ID corresponding to the given point.
        Raises:
            ValueError: If the point (x, y) is out of the image dimensions.
        """
        
        if not (0 <= x < self.w and 0 <= y < self.h):
            raise ValueError(f"Point {x}, {y} is out of image dimensions (0, 0, {self.w}, {self.h})")

        col = x // self.ts
        row = y // self.ts
        tile_id = self.rc_to_tileid(row, col)
        return tile_id

    def tileid_to_point(self, tile_id: int) -> tuple:
        """
        Convert a tile ID to a point (x, y) in the coordinate system.
        Args:
            tile_id (int): The ID of the tile to convert.
        Returns:
            tuple: A tuple (x, y) representing the coordinates of the tile in the workmag space.
        """

        row, col = self.tileid_to_rc(tile_id)
        x = col * self.ts
        y = row * self.ts
        return (x, y)

    def rc_to_tileid(self, row: int, col: int) -> int:
        """
        Convert row and column indices to a tile ID.
        Args:
            row (int): The row index.
            col (int): The column index.
        Returns:
            int: The tile ID corresponding to the given row and column.
        """

        tile_id = row * math.ceil(self.w / self.ts) + col
        return tile_id

    def tileid_to_rc(self, tile_id: int) -> tuple:
        """
        Convert a tile ID to its corresponding row and column indices.
        Args:
            tile_id (int): The ID of the tile.
        Returns:
            tuple: A tuple containing the row and column indices (row, col).
        """

        tiles_per_row = math.ceil(self.w / self.ts)
        row = tile_id // tiles_per_row
        col = tile_id % tiles_per_row
        return (row, col)

    def get_all_tile_ids_for_image(self) -> list:
        """
        Calculate and return a list of all tile IDs for the image.
        The method computes the total number of tiles required to cover the image
        based on the image width (self.w), image height (self.h), and tile size (self.ts).
        It then returns a list of tile IDs ranging from 0 to total_tiles - 1.
        Returns:
            list: A list of integers representing the tile IDs.
        """

        total_tiles = math.ceil(self.w / self.ts) * math.ceil(self.h / self.ts)
        return list(range(total_tiles))

    def get_bbox_for_tile(self, tile_id: int) -> tuple:
        """
        Calculate the bounding box coordinates for a given tile.
        Args:
            tile_id (int): The unique identifier for the tile.
        Returns:
            tuple: A tuple containing the coordinates (x1, y1, x2, y2) of the bounding box, in the workmag space.
        """

        row, col = self.tileid_to_rc(tile_id)

        x1 = col * self.ts
        y1 = row * self.ts
        x2 = x1 + self.ts
        y2 = y1 + self.ts

        return (x1, y1, x2, y2)

def tile_intersects_mask_shapely(image_id: int, annotatation_class_id: int, tile_id: int) -> bool:
    image = get_image_by_id(image_id)
    work_tilesize = get_annotation_class_by_id(annotatation_class_id).work_tilesize

    bbox = get_bbox_for_tile(work_tilesize, image.base_width, image.base_height, tile_id)
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
    work_tilesize = get_annotation_class_by_id(annotation_class_id).work_tilesize
    
    # Load GeoJSON mask (assuming polygon)
    model = create_dynamic_model(build_annotation_table_name(image_id, 1, is_gt=True))
    mask_geojson = get_annotation_query(model).all()

    polygons = []

    scale_factor = 1/work_tilesize
    for annotation in mask_geojson:
        shapely_polygon = shapely.from_geojson(annotation.polygon)
        scaled_polygon = scale(shapely_polygon, xfact=scale_factor, yfact=scale_factor, origin=(0, 0))
        polygons.append(np.floor(scaled_polygon.exterior.coords).astype(np.int32))


    # Create empty mask image
    mask_shape = np.ceil(np.array([image.base_height, image.base_width]) / work_tilesize).astype(np.int32)
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
    tile_ids = [rc_to_tileid(work_tilesize, image.base_width, image.base_height, row, col) for row, col in zip(filled_rows, filled_cols)]

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
        bbox = get_bbox_for_tile(annotation_class.work_tilesize, image.base_width, image.base_height, tile_id)
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