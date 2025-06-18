import numpy as np
from shapely.affinity import scale
from shapely.geometry import Polygon, shape
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import case, update, select
from quickannotator.db.crud.annotation import create_dynamic_model
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor, get_tilespace
from quickannotator.constants import MASK_CLASS_ID, MASK_DILATION, TileStatus
import quickannotator.constants as constants
from datetime import datetime, timedelta
from quickannotator.db import Dialects, db_session
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.annotation_class import get_annotation_class_by_id
from quickannotator.db.crud.image import get_image_by_id
import quickannotator.db.models as db_models
from quickannotator.db.models import get_model_column_names
import geojson
import cv2

from typing import List
from abc import ABC, abstractmethod

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
    

    def upsert_pred_tiles(self, image_id: int, annotation_class_id: int, tile_ids: List[int], pred_status: TileStatus=TileStatus.UNSEEN, process_owns_tile=False) -> List[db_models.Tile]:
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
    def delete_tiles(image_ids: int | list[int] = None, annotation_class_ids: int | list[int] = None) -> None:
        """
        Deletes tiles from the database.

        Args:
            image_id (int or list[int], optional): The ID(s) of the image(s). If None, do not filter by image_id.
            annotation_class_id (int or list[int], optional): The ID(s) of the annotation class(es). If None, do not filter by annotation_class_id.
        """
        stmt = db_models.Tile.__table__.delete()

        if image_ids is not None:
            image_ids = image_ids if isinstance(image_ids, list) else [image_ids]
            stmt = stmt.where(db_models.Tile.image_id.in_(image_ids))

        if annotation_class_ids is not None:
            annotation_class_ids = annotation_class_ids if isinstance(annotation_class_ids, list) else [annotation_class_ids]
            stmt = stmt.where(db_models.Tile.annotation_class_id.in_(annotation_class_ids))

        db_session.execute(stmt)
        db_session.commit()


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
    def get_tile_ids_intersecting_mask(image_id: int, annotation_class_id: int, mask_dilation: int=constants.MASK_DILATION) -> tuple[list, np.ndarray, list]:
        # Get the mask geojson polygons
        tissue_mask_store = AnnotationStore(image_id, MASK_CLASS_ID, True, False)
        mask_geojson: geojson.Polygon = [geojson.loads(ann.polygon) for ann in tissue_mask_store.get_all_annotations()]    # Scales mask to base mag NOTE: potentially optimize using orjson.loads
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

    @staticmethod
    @abstractmethod
    def get_pending_inference_tiles(annotation_class_id: int, batch_size_infer: int, dialect: Dialects) -> list[db_models.Tile]:
        subquery = (
            select(db_models.Tile.id)
            .where(db_models.Tile.annotation_class_id == annotation_class_id,
                db_models.Tile.pred_status == TileStatus.STARTPROCESSING)
            .order_by(db_models.Tile.pred_datetime.desc()) # Order by pred_datetime to get the most recent tiles first
            .limit(batch_size_infer)
        )

        if dialect == Dialects.POSTGRESQL:
            subquery = subquery.with_for_update(skip_locked=True)

        tiles = db_session.execute(
            update(db_models.Tile)
            .where(db_models.Tile.id.in_(subquery))
            .where(db_models.Tile.pred_status == TileStatus.STARTPROCESSING)  # Ensures another worker hasn't claimed it
            .values(pred_status=TileStatus.PROCESSING,pred_datetime=datetime.now())
            .returning(db_models.Tile)
        ).scalars().all()
        
        db_session.expunge_all()


        return tiles if tiles else None
    
    @staticmethod
    @abstractmethod
    def get_workers_tiles(annotation_class_id: int, boost_count: int, dialect: Dialects) -> db_models.Tile:
        subquery = (
            select(db_models.Tile.id)
            .where(db_models.Tile.annotation_class_id == annotation_class_id,
                db_models.Tile.gt_datetime.isnot(None))
            .order_by(db_models.Tile.gt_counter.asc(), db_models.Tile.gt_datetime.asc())  # Prioritize under-used, then newest
            .limit(1)
        )

        if dialect == Dialects.POSTGRESQL:
            subquery = subquery.with_for_update(skip_locked=True)
            

        tile = db_session.execute(
            update(db_models.Tile)
            .where(db_models.Tile.id == subquery.scalar_subquery())
            .values(gt_counter=(
                    # Only increment selection_count if it's less than max_selections
                    case(
                        (db_models.Tile.gt_counter < boost_count, db_models.Tile.gt_counter + 1),
                        else_=db_models.Tile.gt_counter
                    )
                ),
                gt_datetime=datetime.now())
            .returning(db_models.Tile)
        ).scalar()

        if tile:
            db_session.expunge(tile)
            return tile
        else:
            return

class PostgresTileStore(TileStore):
    def __init__(self):
        super().__init__(insert_method=pg_insert)

    @staticmethod
    def get_pending_inference_tiles(annotation_class_id, batch_size_infer):
        return TileStore.get_pending_inference_tiles(annotation_class_id, batch_size_infer, Dialects.POSTGRESQL)

    @staticmethod
    def get_workers_tiles(annotation_class_id, boost_count):
        return TileStore.get_workers_tiles(annotation_class_id, boost_count, Dialects.POSTGRESQL)
        
class SQLiteTileStore(TileStore):
    def __init__(self):
        super().__init__(insert_method=sqlite_insert)

    @staticmethod
    def get_pending_inference_tiles(annotation_class_id, batch_size_infer):
        return TileStore.get_pending_inference_tiles(annotation_class_id, batch_size_infer, Dialects.SQLITE)
    
    @staticmethod
    def get_workers_tiles(annotation_class_id, boost_count):
        return TileStore.get_workers_tiles(annotation_class_id, boost_count, Dialects.SQLITE)


class TileStoreFactory():
    @staticmethod
    def get_tilestore() -> PostgresTileStore | SQLiteTileStore:
        dialect_name = db_session.bind.dialect.name

        if dialect_name == Dialects.POSTGRESQL.value:
            return PostgresTileStore()
        elif dialect_name == Dialects.SQLITE.value:
            return SQLiteTileStore()
        else:
            raise ValueError(f"Unsupported dialect: {dialect_name}")

        
