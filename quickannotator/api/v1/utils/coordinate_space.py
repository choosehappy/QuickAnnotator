import large_image
import os
import numpy as np
import math
import geojson
from quickannotator.db.crud.annotation_class import get_annotation_class_by_id
from quickannotator.db.crud.image import get_image_by_id
from quickannotator.constants import BASE_PATH
from quickannotator.db.fsmanager import fsmanager


class TileSpace:
    """
    A helper class for working with an image divided into tiles.

    **Important:** All inputs (tilesize, image dimensions, bounding boxes, and coordinates)
    must be provided in the same coordinate space. If your system has multiple magnifications
    or transformations, ensure consistency before using this class.

    This class provides methods to:
    - Convert between points, tiles, and bounding boxes.
    - Retrieve tile IDs within a given bounding box.
    - Handle image boundaries safely.
    """
    def __init__(self, tilesize: int, image_width: int, image_height: int):
        """
        Initializes the TileSpace with the given tile size and image dimensions.

        **All parameters must be in the same coordinate space (e.g., either the working magnification
        space or the base magnification space).** Using mixed coordinate spaces may lead to incorrect
        calculations.

        Args:
            tilesize (int): The size of each tile in the given coordinate space.
            image_width (int): The width of the image in the same coordinate space.
            image_height (int): The height of the image in the same coordinate space.
        """
        self.ts = tilesize
        self.w = image_width
        self.h = image_height

    def get_tile_ids_within_bbox(self, bbox: list[float]) -> list:
        """
        Get the tile IDs within a specified bounding box.
        This method calculates the tile IDs that fall within the given bounding box
        coordinates. The bounding box coordinates are adjusted to ensure they are
        within the image dimensions.
        Args:
            bbox (list[float]): A list of four floats representing the bounding box
                                coordinates [x1, y1, x2, y2].
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
        start_col = int(x1 // self.ts)
        end_col = int(math.ceil(x2 / self.ts)) - 1
        start_row = int(y1 // self.ts)
        end_row = int(math.ceil(y2 / self.ts)) - 1

        # Create a mesh grid of tile coordinates
        cols, rows = np.meshgrid(np.arange(start_col, end_col + 1), np.arange(start_row, end_row + 1))

        # Flatten the mesh grid and calculate tile IDs
        tile_ids = (rows * tiles_per_row + cols).flatten().tolist()

        return tile_ids

    def point_to_tileid(self, x: float, y: float) -> int:
        """
        Convert a point (x, y) to a tile ID.
        Args:
            x (float): The x-coordinate of the point.
            y (float): The y-coordinate of the point.
        Returns:
            int: The tile ID corresponding to the given point.
        Raises:
            ValueError: If the point (x, y) is out of the image dimensions.
        """

        if not (0 <= x < self.w and 0 <= y < self.h):
            raise ValueError(f"Point {x}, {y} is out of image dimensions (0, 0, {self.w}, {self.h})")

        col = int(x // self.ts)
        row = int(y // self.ts)
        tile_id = self.rc_to_tileid(row, col)
        return tile_id

    def tileid_to_point(self, tile_id: int) -> tuple:
        """
        Convert a tile ID to a point (x, y) in the coordinate system.
        Args:
            tile_id (int): The ID of the tile to convert.
        Returns:
            tuple: A tuple (x, y) representing the coordinates of the tile
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
            tuple: A tuple containing the coordinates (x1, y1, x2, y2) of the bounding box.
        """

        row, col = self.tileid_to_rc(tile_id)

        x1 = col * self.ts
        y1 = row * self.ts
        x2 = x1 + self.ts
        y2 = y1 + self.ts

        return (x1, y1, x2, y2)

def get_tilespace(image_id: int, annotation_class_id: int, in_work_mag: bool=True) -> TileSpace:
    image = get_image_by_id(image_id)
    annotation_class = get_annotation_class_by_id(annotation_class_id)
    r = base_to_work_scaling_factor(image_id, annotation_class_id)
    if in_work_mag:
        image_work_width = image.base_width * r
        image_work_height = image.base_height * r
        return TileSpace(annotation_class.work_tilesize, image_work_width, image_work_height)
    else:   # return
        base_tilesize = annotation_class.work_tilesize / r
        return TileSpace(base_tilesize, image.base_width, image.base_height)


def base_to_work_scaling_factor(image_id: int, annotation_class_id: int) -> float:
    """
    Get the scale factor for annotations based on the base and working magnifications.
    Args:
        image_id (int): The ID of the image to retrieve.
        annotation_class_id (int): The ID of the annotation class to use for scaling.
    Returns:
        float: The scale factor to apply to the annotations.
    """
    relative_path = get_image_by_id(image_id).path
    full_path = fsmanager.nas_read.relative_to_global(relative_path)
    ts = large_image.getTileSource(full_path)
    base_mag = float(ts.getMetadata()['magnification'])
    work_mag = float(get_annotation_class_by_id(annotation_class_id).work_mag)
    return work_mag / base_mag