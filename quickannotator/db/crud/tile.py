import numpy as np
from shapely.affinity import scale
from shapely.geometry import Polygon, shape
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import case, update
from quickannotator.db.crud.annotation import create_dynamic_model
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor, get_tilespace
from quickannotator.constants import MASK_CLASS_ID, MASK_DILATION, TileStatus
import quickannotator.constants as constants
from datetime import datetime, timedelta
from quickannotator.db import db_session
from quickannotator.db.crud.annotation import get_annotation_query
from quickannotator.db.crud.annotation_class import get_annotation_class_by_id
from quickannotator.db.crud.image import get_image_by_id
import quickannotator.db.models as db_models
from quickannotator.db.models import get_model_column_names
import geojson
import cv2

from typing import List
from abc import ABC

from quickannotator.db.crud.annotation import build_annotation_table_name


class TileStore(ABC):   # Only an ABC to prevent instantiation
    def __init__(self, insert_method=None):
        self.insert_method = insert_method

    def _upsert_tiles(self, image_id, annotation_class_id, tile_ids, insert_fields, update_fields):
        """
        Inserts new tiles or updates existing tiles in the database.
        This function attempts to insert new tiles with the given annotation_class_id, image_id, and tile_ids.
        If tiles with the same annotation_class_id, image_id, and tile_ids already exist, it updates the relevant fields.

        Args:
            image_id (int): The ID of the image.
            annotation_class_id (int): The ID of the annotation class.
            tile_ids (List[int]): The IDs of the tiles.
            insert_fields (dict): Additional fields to insert into the tile.
            update_fields (dict): Additional fields to update in the tile.
        Returns:
            List[models.Tile]: The tiles that were inserted or updated.
        """
        if len(tile_ids) == 0:
            return []

        stmt = self.insert_method(db_models.Tile).values(
            [
                {
                    'annotation_class_id': annotation_class_id,
                    'image_id': image_id,
                    'tile_id': tile_id,
                    **insert_fields
                }
                for tile_id in tile_ids
            ]
        ).on_conflict_do_update(
            index_elements=['annotation_class_id', 'image_id', 'tile_id'],
            set_=update_fields
        ).returning(
            *get_model_column_names(db_models.Tile)
        )

        tiles = db_session.execute(stmt).all()
        db_session.commit()
        return tiles


    def upsert_gt_tiles(self, image_id: int, annotation_class_id: int, tile_ids: List[int]) -> List[db_models.Tile]:
        """
        Inserts new ground truth tiles or updates existing ground truth tiles in the database.
        This function attempts to insert new ground truth tiles with the given annotation_class_id, image_id, and tile_ids.
        If ground truth tiles with the same annotation_class_id, image_id, and tile_ids already exist, it updates the relevant fields.

        Args:
            image_id (int): The ID of the image.
            annotation_class_id (int): The ID of the annotation class.
            tile_ids (List[int]): The IDs of the tiles.

        Returns:
            List[models.Tile]: The tiles that were inserted or updated.
        """
        
        current_time = datetime.now()
        update_fields = {
            'gt_counter': 0,
            'gt_datetime': current_time
        }

        tiles = self._upsert_tiles(
            image_id=image_id,
            annotation_class_id=annotation_class_id,
            tile_ids=tile_ids,
            insert_fields=update_fields,
            update_fields=update_fields
        )
        return tiles
    

    def upsert_pred_tiles(self, image_id: int, annotation_class_id: int, tile_ids: List[int], pred_status: TileStatus, process_owns_tile=False) -> List[db_models.Tile]:
        """
        Inserts new prediction tiles or updates existing prediction tiles in the database.
        This function attempts to insert new prediction tiles with the given annotation_class_id, image_id, and tile_ids.
        If prediction tiles with the same annotation_class_id, image_id, and tile_ids already exist, it updates the relevant fields.

        Args:
            image_id (int): The ID of the image.
            annotation_class_id (int): The ID of the annotation class.
            tile_ids (List[int]): The IDs of the tiles.
            pred_status (TileStatus): The status of the tile prediction.
            process_owns_tile (bool, optional): If True, updates tiles regardless of their current status. Defaults to False. Only a ray actor should set this to True.

        Returns:
            List[models.Tile]: The tiles that were inserted or updated.
        """

        if pred_status is None:
            raise ValueError("pred_status cannot be None.")
        
        current_time = datetime.now()
        insert_fields = {
            'pred_status': pred_status,
            'pred_datetime': current_time
        }
        
        if process_owns_tile:
            update_fields = insert_fields
        else:
            expiration_thresh = current_time - timedelta(minutes=constants.TILE_PRED_EXPIRE)

            tile_is_unseen_or_stale = case((db_models.Tile.pred_status == TileStatus.UNSEEN, 1),
                (
                    (db_models.Tile.pred_status == TileStatus.DONEPROCESSING) & 
                    (db_models.Tile.pred_datetime <= expiration_thresh), 1
                ),
                else_=0
            )

            update_fields = {
                'pred_status': case((tile_is_unseen_or_stale == 1, pred_status), else_=db_models.Tile.pred_status),
                'pred_datetime': case((tile_is_unseen_or_stale == 1, current_time), else_=db_models.Tile.pred_datetime)
            }

        tiles = self._upsert_tiles(
            image_id=image_id,
            annotation_class_id=annotation_class_id,
            tile_ids=tile_ids,
            insert_fields=insert_fields,
            update_fields=update_fields
        )
        return tiles

    @staticmethod
    def get_tiles_by_tile_ids(image_id: int, annotation_class_id: int, tile_ids: list[int], hasgt=False) -> list[db_models.Tile]:
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
        query = db_session.query(db_models.Tile).filter(
            db_models.Tile.image_id == image_id,
            db_models.Tile.annotation_class_id == annotation_class_id,
            db_models.Tile.tile_id.in_(tile_ids)
        )

        if hasgt:
            query = query.filter(db_models.Tile.gt_datetime.isnot(None))

        return query.all()
    
    @staticmethod
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
    
    @staticmethod
    def get_tile_ids_intersecting_mask(image_id: int, annotation_class_id: int, mask_dilation: int) -> tuple[list, np.ndarray, list]:
        # This function operates in the base magnification space
        mask_work_to_base_scale_factor = 1 / base_to_work_scaling_factor(image_id=image_id, annotation_class_id=MASK_CLASS_ID)

        # Get the mask geojson polygons
        model = create_dynamic_model(build_annotation_table_name(image_id, MASK_CLASS_ID, is_gt=True))
        mask_geojson: geojson.Polygon = [geojson.loads(ann.polygon) for ann in get_annotation_query(model, mask_work_to_base_scale_factor).all()]    # Scales mask to base mag
        tilestore = TileStoreFactory.get_tilestore()

        tile_ids, mask, processed_polygons = tilestore.get_tile_ids_intersecting_polygons(image_id, annotation_class_id, mask_geojson, mask_dilation)

        return tile_ids, mask, processed_polygons

    @staticmethod
    def get_tile(image_id: int, annotation_class_id: int, tile_id: int) -> db_models.Tile:
        result = db_session.query(db_models.Tile).filter_by(
            annotation_class_id=annotation_class_id,
            image_id=image_id,
            tile_id=tile_id
        ).first()
        return result
    
    @staticmethod
    def reset_all_PROCESSING_tiles(annotation_class_id: int):
        stmt = update(db_models.Tile).where(
            db_models.Tile.annotation_class_id == annotation_class_id,
            db_models.Tile.pred_status == TileStatus.PROCESSING
        ).values(
            pred_status=TileStatus.UNSEEN,
            pred_datetime=None
        )
        db_session.execute(stmt)
        db_session.commit()
    


class PostgresTileStore(TileStore):
    def __init__(self):
        super().__init__(insert_method=pg_insert)

        
class SQLiteTileStore(TileStore):
    def __init__(self):
        super().__init__(insert_method=sqlite_insert)


class TileStoreFactory():
    @staticmethod
    def get_tilestore() -> TileStore:
        dialect_name = db_session.bind.dialect.name

        if dialect_name == 'postgresql':
            return PostgresTileStore()
        elif dialect_name == 'sqlite':
            return SQLiteTileStore()
        else:
            raise ValueError(f"Unsupported dialect: {dialect_name}")

        
