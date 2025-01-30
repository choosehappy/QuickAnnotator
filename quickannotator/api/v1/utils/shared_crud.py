from datetime import datetime
from sqlalchemy.orm import aliased, sessionmaker, Session, Query, DeclarativeBase
import quickannotator.db as qadb
from quickannotator.db import build_annotation_table_name, create_dynamic_model
import shapely
import json
from sqlalchemy import func, text


# TODO: Remove session from params
def get_tile(session: Session, annotation_class_id: int, image_id: int, tile_id: int) -> qadb.Tile:
    result = session.query(qadb.Tile).filter_by(
        annotation_class_id=annotation_class_id,
        image_id=image_id,
        tile_id=tile_id
    ).first()
    return result


def compute_custom_metrics() -> dict:
    return {"iou": 0.5}

# TODO: Remove session from params
def insert_new_annotation(session, image_id, annotation_class_id, is_gt, polygon: shapely.geometry.Polygon):
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    model = create_dynamic_model(table_name)

    new_annotation = model(
        image_id=None,
        annotation_class_id=None,
        isgt=None,
        centroid=polygon.centroid.wkt,
        polygon=polygon.wkt,
        area=polygon.area,
        custom_metrics=compute_custom_metrics(),
        datetime=datetime.now()
    )
    session.add(new_annotation)
    session.commit()
    return new_annotation

def get_annotation_query(model) -> Query:
    '''
    Constructs a SQLAlchemy query to retrieve annotation data from the database. The Annotation model itself could alternatively
    be used to automatically cast the polygon and centroid as geojson using colum_property() or hybrid_property decorators, but
    it does not seem possible with this approach to perform this conversion instead of (rather than in addition to) returning the
    WKT representation of the geometry. 
    Args:
        model: The SQLAlchemy model class representing the annotation table.
    Returns:
        Query: A SQLAlchemy query object that retrieves the following fields from the annotation table:
            - id: The unique identifier of the annotation.
            - tile_id: The identifier of the tile associated with the annotation.
            - centroid: The centroid of the annotation polygon in GeoJSON format.
            - polygon: The annotation polygon in GeoJSON format.
            - area: The area of the annotation polygon.
            - custom_metrics: Custom metrics associated with the annotation.
            - datetime: The datetime when the annotation was created or last modified.
    '''

    query = qadb.db.session.query(
        model.id,
        model.tile_id,
        func.ST_AsGeoJSON(model.centroid).label('centroid'),
        func.ST_AsGeoJSON(model.polygon).label('polygon'),
        model.area,
        model.custom_metrics,
        model.datetime
    )

    return query
