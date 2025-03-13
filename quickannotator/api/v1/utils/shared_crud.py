from shapely.affinity import scale
from shapely.geometry.base import BaseGeometry
from sqlalchemy import func, insert
from datetime import datetime
from typing import List
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Query
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor, get_tilespace
from quickannotator.constants import TileStatus
from quickannotator.db import db_session, Base
import quickannotator.db.models as models
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from sqlalchemy.ext.declarative import declarative_base


def get_tile(annotation_class_id: int, image_id: int, tile_id: int) -> models.Tile:
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

def get_basemag_annotation_query(model, image_id, annotation_class_id):
    """
    Generate a query for annotations so that they are automatically scaled by the base magnification of the image.
    Args:
        model: The model to query annotations from.
        image_id (int): The ID of the image to retrieve.
        annotation_class_id (int): The ID of the annotation class to use for scaling.
    Returns:
        Query: A query object for retrieving annotations scaled to the appropriate magnification.
    """
    
    scale_factor = base_to_work_scaling_factor(image_id, annotation_class_id)
    return get_annotation_query(model, scale_factor)


def upsert_tiles(image_id: int, annotation_class_id: int, tile_ids: list[int], seen: TileStatus=None, hasgt: bool=None):
    """
    Inserts new tiles or updates existing tiles in the database.
    This function attempts to insert new tiles with the given annotation_class_id, image_id, and tile_ids.
    If tiles with the same annotation_class_id, image_id, and tile_ids already exist, it updates the 'seen'
    and 'hasgt' fields if their values are provided.
    Args:
        annotation_class_id (int): The ID of the annotation class.
        image_id (int): The ID of the image.
        tile_ids (list[int]): A list of tile IDs.
        seen (TileStatus, optional): The status indicating if the tiles have been seen. Defaults to None.
        hasgt (bool, optional): A flag indicating if the tiles have ground truth. Defaults to None.
    Returns:
        ResultProxy: The result of the database execution
    """

    update_fields = {}
    if seen is not None:    # Only update the 'seen' field if the value is provided
        update_fields['seen'] = seen
    if hasgt is not None:   # Only update the 'hasgt' field if the value is provided
        update_fields['hasgt'] = hasgt

    stmt = insert(models.Tile).values([
        {
            'annotation_class_id': annotation_class_id,
            'image_id': image_id,
            'tile_id': tile_id,
            **update_fields
        } for tile_id in tile_ids
    ]).on_conflict_do_update(
        index_elements=['annotation_class_id', 'image_id', 'tile_id'],
        set_=update_fields
    )

    result = db_session.execute(stmt)
    db_session.commit()

    return result


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
    # TODO: make this function applicable to predicted annotations, not just ground truths.
    def insert_annotations(self, polygons: List[BaseGeometry]) -> List[models.Annotation]:
        # in_work_mag is true because we expect the polygons are scaled at this point.
        tilespace = get_tilespace(self.image_id, self.annotation_class_id, in_work_mag=True)
        new_annotations = []
        for polygon in polygons:
            scaled_polygon = self.scale_polygon(polygon, self.scaling_factor)
            tile_id = tilespace.point_to_tileid(scaled_polygon.centroid.x, scaled_polygon.centroid.y)

            new_annotations.append({
                "tile_id": tile_id,  # Ensure correct value
                "centroid": scaled_polygon.centroid.wkt,
                "polygon": scaled_polygon.wkt,
                "area": scaled_polygon.area,
                "custom_metrics": compute_custom_metrics(),  # Add appropriate custom metrics if needed
                "datetime": datetime.now()
            })
        stmt = insert(self.model).returning(self.model.id).values(new_annotations)
        ids = db_session.scalars(stmt).all()
        result = self.get_annotations_by_ids(annotation_ids=ids)
        tile_ids = [ann.tile_id for ann in result]
        
        if self.is_gt:
            upsert_tiles(self.image_id, self.annotation_class_id, tile_ids, seen=None, hasgt=True)
        else:
            upsert_tiles(self.image_id, self.annotation_class_id, tile_ids, seen=TileStatus.DONEPROCESSING, hasgt=None)
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
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter(func.ST_Intersects(self.model.polygon, scaled_polygon.wkt)).all()
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
    def delete_annotation(self, annotation_id: int):
        result = db_session.query(self.model).filter(self.model.id == annotation_id).delete()
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

