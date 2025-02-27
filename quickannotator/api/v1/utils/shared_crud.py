from datetime import datetime
from sqlalchemy.orm import aliased, sessionmaker, Session, Query, DeclarativeBase
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor
import quickannotator.db as qadb
from quickannotator.db.utils import build_annotation_table_name
import shapely
import json
from sqlalchemy import func, text


from quickannotator.db.utils import create_dynamic_model
import quickannotator.db.models
from quickannotator.db import db_session
from flask import current_app


def get_tile(annotation_class_id: int, image_id: int, tile_id: int) -> quickannotator.db.models.Tile:
    result = db_session.query(quickannotator.db.models.Tile).filter_by(
        annotation_class_id=annotation_class_id,
        image_id=image_id,
        tile_id=tile_id
    ).first()
    return result


def compute_custom_metrics() -> dict:
    return {"iou": 0.5}

def insert_new_annotation(image_id, annotation_class_id, is_gt, tile_id, polygon: shapely.geometry.Polygon):
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    model = create_dynamic_model(table_name)

    new_annotation = model(
        image_id=None,
        annotation_class_id=None,
        isgt=None,
        tile_id=tile_id,
        centroid=polygon.centroid.wkt,
        polygon=polygon.wkt,
        area=polygon.area,
        custom_metrics=compute_custom_metrics(),
        datetime=datetime.now()
    )
    db_session.add(new_annotation)
    db_session.commit()
    return new_annotation

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
    
    if scale_factor == 1.0:
        query = db_session.query(
            model.id,
            model.tile_id,
            func.ST_AsGeoJSON(model.centroid).label('centroid'),
            func.ST_AsGeoJSON(model.polygon).label('polygon'),
            model.area,
            model.custom_metrics,
            model.datetime
        )
    else:
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

