from sqlalchemy.engine import Dialect
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import case, update
from quickannotator.constants import TileStatus
import quickannotator.constants as constants
from datetime import datetime, timedelta
from quickannotator.db import db_session
import quickannotator.db.models as models
from quickannotator.db.models import get_model_column_names

from typing import List
from abc import ABC


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

        stmt = self.insert_method(models.Tile).values(
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
            *get_model_column_names(models.Tile)
        )

        tiles = db_session.execute(stmt).all()
        db_session.commit()
        return tiles


    def upsert_gt_tiles(self, image_id: int, annotation_class_id: int, tile_ids: List[int]) -> List[models.Tile]:
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
    

    def upsert_pred_tiles(self, image_id: int, annotation_class_id: int, tile_ids: List[int], pred_status: TileStatus, process_owns_tile=False) -> List[models.Tile]:
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

            tile_is_unseen_or_stale = case((models.Tile.pred_status == TileStatus.UNSEEN, 1),
                (
                    (models.Tile.pred_status == TileStatus.DONEPROCESSING) & 
                    (models.Tile.pred_datetime <= expiration_thresh), 1
                ),
                else_=0
            )

            update_fields = {
                'pred_status': case((tile_is_unseen_or_stale == 1, pred_status), else_=models.Tile.pred_status),
                'pred_datetime': case((tile_is_unseen_or_stale == 1, current_time), else_=models.Tile.pred_datetime)
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
    def get_tile(image_id: int, annotation_class_id: int, tile_id: int) -> models.Tile:
        result = db_session.query(models.Tile).filter_by(
            annotation_class_id=annotation_class_id,
            image_id=image_id,
            tile_id=tile_id
        ).first()
        return result
    
    @staticmethod
    def reset_all_PROCESSING_tiles(annotation_class_id: int):
        stmt = update(models.Tile).where(
            models.Tile.annotation_class_id == annotation_class_id,
            models.Tile.pred_status == TileStatus.PROCESSING
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
        
