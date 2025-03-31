from shapely.affinity import scale
from shapely.geometry.base import BaseGeometry
from sqlalchemy import func
from datetime import datetime, timedelta
import sqlalchemy
from typing import List
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Query
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor, get_tilespace
from quickannotator.constants import TileStatus
from quickannotator.db import db_session, Base
import quickannotator.db.models as models
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from sqlalchemy.ext.declarative import declarative_base
import quickannotator.constants as constants


def get_tile(image_id: int, annotation_class_id: int, tile_id: int) -> models.Tile:
    result = db_session.query(models.Tile).filter_by(
        annotation_class_id=annotation_class_id,
        image_id=image_id,
        tile_id=tile_id
    ).first()
    return result


def compute_custom_metrics() -> dict:
    return {"iou": 0.5}

def get_annotation_query(model, scale_factor: float=1.0) -> Query:
    '''
    Constructs a SQLAlchemy query to retrieve and scale annotation data from the database.
    Args:
        model: The SQLAlchemy model class representing the annotation table.
        scale_factor: The factor by which to scale the geometries.
    Returns:
        Query: A SQLAlchemy query object that retrieves the following fields from the annotation table:
            - id: The unique identifier of the annotation.
            - tile_id: The identifier of the tile associated with the annotation.
            - centroid: The scaled centroid of the annotation polygon in GeoJSON format.
            - polygon: The scaled annotation polygon in GeoJSON format.
            - area: The area of the annotation polygon.
            - custom_metrics: Custom metrics associated with the annotation.
            - datetime: The datetime when the annotation was created or last modified.
    '''

    if scale_factor <= 0:
        raise ValueError("scale_factor must be greater than 0.")
    
    query = db_session.query(
        model.id,
        model.tile_id,
        func.ST_AsGeoJSON(func.ST_Scale(model.centroid, scale_factor, scale_factor)).label('centroid'),
        func.ST_AsGeoJSON(func.ST_Scale(model.polygon, scale_factor, scale_factor)).label('polygon'),
        model.area,
        model.custom_metrics,
        model.datetime
    )

    return query

def upsert_gt_tiles(image_id: int, annotation_class_id: int, tile_ids: List[int]) -> List[models.Tile]:
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

    if len(tile_ids) == 0:
        return []
    
    update_fields = {
        'gt_counter': 0,
        'gt_datetime': datetime.now()
    }
    
    stmt = insert(models.Tile).values(
        [
            {
                'annotation_class_id': annotation_class_id,
                'image_id': image_id,
                'tile_id': tile_id,
                **update_fields
            }
            for tile_id in tile_ids
        ]
    ).on_conflict_do_update(
        index_elements=['annotation_class_id', 'image_id', 'tile_id'],
        set_=update_fields
    ).returning(
        *[getattr(models.Tile, column.name) for column in models.Tile.__table__.columns]   # Can't use models.Tile with on_conflict_do_update
    )

    tiles = db_session.execute(stmt).all()
    db_session.commit()
    return tiles

def upsert_pred_tiles(image_id: int, annotation_class_id: int, tile_ids: List[int], pred_status: TileStatus, process_owns_tile=False) -> List[models.Tile]:
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

    if len(tile_ids) == 0:
        return []

    if pred_status is None:
        raise ValueError("pred_status cannot be None.")
    
    update_fields = {
        'pred_status': pred_status,
        'pred_datetime': datetime.now()
    }
    
    if process_owns_tile:
        set = update_fields
    else:
        current_time = datetime.now()
        expiration_thresh = current_time - timedelta(minutes=constants.TILE_PRED_EXPIRE)
        set = {
            'pred_status': sqlalchemy.case(
                (models.Tile.pred_status == TileStatus.UNSEEN, pred_status),
                (
                    (models.Tile.pred_status == TileStatus.DONEPROCESSING) & 
                    (models.Tile.pred_datetime <= expiration_thresh), pred_status
                ),
            else_=models.Tile.pred_status,
            ),
            'pred_datetime': sqlalchemy.case(
                (models.Tile.pred_status == TileStatus.UNSEEN, datetime.now()),
                (
                    (models.Tile.pred_status == TileStatus.DONEPROCESSING) & 
                    (models.Tile.pred_datetime <= expiration_thresh), datetime.now()
                ),
            else_=models.Tile.pred_datetime,
            )
        }

    stmt = insert(models.Tile).values(
        [
            {
                'annotation_class_id': annotation_class_id,
                'image_id': image_id,
                'tile_id': tile_id,
                **update_fields
            }
            for tile_id in tile_ids
        ]
    ).on_conflict_do_update(
        index_elements=['annotation_class_id', 'image_id', 'tile_id'],
        set_=set
    ).returning(
        *[getattr(models.Tile, column.name) for column in models.Tile.__table__.columns]   # Can't use models.Tile with on_conflict_do_update
    )
    tiles = db_session.execute(stmt).all()
    return tiles


class AnnotationStore:
    def __init__(self, image_id: int, annotation_class_id: int, is_gt: bool, in_work_mag=True, create_table=False):
        """
        Initializes the annotation helper with the given parameters.

        Args:
            image_id (int): The ID of the image.
            annotation_class_id (int): The ID of the annotation class.
            is_gt (bool): A flag indicating whether the annotation is ground truth.
            in_work_mag (bool, optional): If True, all input and output polygons are in working magnification. Defaults to True. 
                If False, all input and output polygons are in base magnification.
            create_table_if_non_existent (bool, optional): If True, creates the annotation table if it does not exist. Defaults to False.

        Attributes:
            image_id (int): The ID of the image.
            annotation_class_id (int): The ID of the annotation class.
            is_gt (bool): A flag indicating whether the annotation is ground truth.
            model: The dynamic model created for the annotation.
            scaling_factor (float): The base to work scaling factor.
        """

        self.image_id = image_id
        self.annotation_class_id = annotation_class_id
        self.is_gt = is_gt
        self.scaling_factor = 1.0 if in_work_mag else base_to_work_scaling_factor(image_id, annotation_class_id)

        if create_table:
            model = self.create_annotation_table(image_id, annotation_class_id, is_gt)
            self.model = model
        else:
            self.model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, is_gt=is_gt))

    # CREATE
    # TODO: consider adding optional parameter to allow tileids to be passed in.
    def insert_annotations(self, polygons: List[BaseGeometry], tile_ids: List[int] | int=None) -> List[models.Annotation]:
        # Initial validation
        if len(polygons) == 0:
            return []
        
        if isinstance(tile_ids, int):
            tile_ids = [tile_ids] * len(polygons)
        
        if tile_ids is not None and len(polygons) != len(tile_ids):
            raise ValueError("The lengths of polygons and tile_ids must match if tile_ids is a list.")

        # in_work_mag is true because we expect the polygons are scaled at this point.
        tilespace = get_tilespace(self.image_id, self.annotation_class_id, in_work_mag=True)
        new_annotations = []

        for i, polygon in enumerate(polygons):
            scaled_polygon = self.scale_polygon(polygon, self.scaling_factor)

            # Determine tile_id based on provided parameters or calculate it
            if tile_ids is not None:
                current_tile_id = tile_ids[i]
            else:
                current_tile_id = tilespace.point_to_tileid(scaled_polygon.centroid.x, scaled_polygon.centroid.y)

            new_annotations.append({
                "tile_id": current_tile_id,  # Ensure correct value
                "centroid": scaled_polygon.centroid.wkt,
                "polygon": scaled_polygon.wkt,
                "area": scaled_polygon.area,
                "custom_metrics": compute_custom_metrics(),  # Add appropriate custom metrics if needed
                "datetime": datetime.now()
            })

        stmt = sqlalchemy.insert(self.model).returning(self.model.id).values(new_annotations)
        ids = db_session.scalars(stmt).all()
        result = self.get_annotations_by_ids(annotation_ids=ids)    # Must do this otherwise scaling etc. does not apply.
        tile_ids = [ann.tile_id for ann in result]
        
        if self.is_gt:
            upsert_gt_tiles(self.image_id, self.annotation_class_id, tile_ids)
        else:
            upsert_pred_tiles(self.image_id, self.annotation_class_id, tile_ids, pred_status=TileStatus.DONEPROCESSING, process_owns_tile=True)
        return result


    # READ
    def get_annotation_by_id(self, annotation_id: int) -> models.Annotation:
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter_by(id=annotation_id).first()
        return result
    
    def get_annotations_by_ids(self, annotation_ids: List[int]) -> List[models.Annotation]:
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter(self.model.id.in_(annotation_ids)).all()
        return result

    def get_annotations_for_tiles(self, tile_ids: List[int]) -> List[models.Annotation]:
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter(self.model.tile_id.in_(tile_ids)).all()
        return result

    def get_annotations_within_poly(self, polygon: BaseGeometry) -> List[models.Annotation]:
        scaled_polygon = self.scale_polygon(polygon, self.scaling_factor)
        # NOTE: Sqlite may not use the spatial index here.
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter(func.ST_Intersects(self.model.polygon, func.ST_GeomFromText(scaled_polygon.wkt, 0))).all()
        return result

    # UPDATE
    def update_annotation(self, annotation_id: int, polygon: BaseGeometry) -> models.Annotation:
        scaled_polygon = self.scale_polygon(polygon, self.scaling_factor)
        tile_id = get_tilespace(self.image_id, self.annotation_class_id).point_to_tileid(
            scaled_polygon.centroid.x, scaled_polygon.centroid.y
        )

        annotation = db_session.query(self.model).filter(self.model.id == annotation_id).first()
        
        if annotation:
            annotation.tile_id = tile_id
            annotation.centroid = scaled_polygon.centroid.wkt
            annotation.polygon = scaled_polygon.wkt
            annotation.area = scaled_polygon.area
            annotation.custom_metrics = compute_custom_metrics()
            annotation.datetime = datetime.now()
            db_session.commit()
            return self.get_annotation_by_id(annotation_id)  # Get the updated annotation by id

        return None  # Handle case where annotation_id is not found


    # DELETE
    def delete_annotation(self, annotation_id: int) -> int:
        """
        Deletes an annotation by its ID.
        Args:
            annotation_id (int): The ID of the annotation to be deleted.
        Returns:
            int: The ID of the deleted annotation if it exists, otherwise None.
        """

        stmt = sqlalchemy.delete(self.model).where(self.model.id == annotation_id).returning(self.model.id)
        result = db_session.execute(stmt).scalar_one_or_none()
        db_session.commit()
        return result
    
    def delete_annotations(self, annotation_ids: List[int]) -> List[int]:
        """
        Deletes multiple annotations by their IDs.
        Args:
            annotation_ids (List[int]): A list of annotation IDs to be deleted.
        Returns:
            List[int]: A list of the IDs of the deleted annotations.
        """

        stmt = sqlalchemy.delete(self.model).where(self.model.id.in_(annotation_ids)).returning(self.model.id)
        result = db_session.execute(stmt).scalars().all()
        db_session.commit()
        return result
    
    def delete_annotations_by_tile(self, tile_id: int) -> List[int]:
        """
        Deletes all annotations associated with a tile.
        Args:
            tile_id (int): The ID of the tile.
        Returns:
            List[int]: A list of the IDs of the deleted annotations.
        """

        stmt = sqlalchemy.delete(self.model).where(self.model.tile_id == tile_id).returning(self.model.id)
        result = db_session.execute(stmt).scalars().all()
        db_session.commit()
        return result

    def delete_all_annotations(self):
        db_session.query(self.model).delete()

    
    @staticmethod
    def create_annotation_table(image_id: int, annotation_class_id: int, is_gt: bool):
        table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt=is_gt)
        table = models.Annotation.__table__.to_metadata(Base.metadata, name=table_name)
        Base.metadata.create_all(bind=db_session.bind, tables=[table])

        return create_dynamic_model(table_name)



    @staticmethod
    def scale_polygon(polygon: BaseGeometry, scaling_factor: float) -> BaseGeometry:   # Added for safety - I've forgotten the origin param several times.
        return scale(polygon, xfact=scaling_factor, yfact=scaling_factor, origin=(0, 0))

