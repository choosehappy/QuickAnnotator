import quickannotator.db as qadb
from sqlalchemy import func, select, text, MetaData, Table
from sqlalchemy.orm import aliased, Session, Query
from typing import List
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import DateTime
import quickannotator.db.models as models
from quickannotator.db import db_session
from quickannotator.api.v1.utils.shared_crud import get_annotation_query
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from shapely.geometry import Polygon
import geojson
from shapely.affinity import scale
from shapely.geometry.base import BaseGeometry


Base = declarative_base()

def annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    # Right now we are selecting by centroid and not polygon.
    stmt = table.select().where(func.ST_Intersects(table.c.centroid, envelope))
    result = db_session.execute(stmt).fetchall()
    return result

def get_annotations_for_tile(image_id: int, annotation_class_id: int, tile_id: int, is_gt: bool) -> List[models.Annotation]:
    model: models.Annotation = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, is_gt))
    scale_factor = base_to_work_scaling_factor(image_id, annotation_class_id)
    result: List[models.Annotation] = get_annotation_query(model, 1/scale_factor).filter_by(tile_id=tile_id).all()
    
    return result

def get_annotations_for_tiles(image_id: int, annotation_class_id: int, tile_ids: List[int], is_gt: bool) -> List[models.Annotation]:
    model: models.Annotation = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, is_gt))
    scale_factor = base_to_work_scaling_factor(image_id, annotation_class_id)
    result: List[models.Annotation] = get_annotation_query(model, 1/scale_factor).filter(model.tile_id.in_(tile_ids)).all()
    
    return result

def get_annotations_within_poly(image_id: int, annotation_class_id: int, is_gt: bool, polygon: geojson.Polygon) -> List[models.Annotation]:
    pass

def annotations_within_bbox_spatial(table_name: str, x1: float, y1: float, x2: float, y2: float) -> List[models.Annotation]:
    stmt = text(f'''
        SELECT ROWID, AsGeoJSON(centroid) as centroid, area, AsGeoJSON(polygon) as polygon, custom_metrics, datetime, annotation_class_id
        FROM "{table_name}"
        WHERE "{table_name}".ROWID IN (
            SELECT ROWID
            FROM SpatialIndex
            WHERE f_table_name = "{table_name}"
            AND f_geometry_column = 'centroid'
            AND search_frame = BuildMbr({x1}, {y1}, {x2}, {y2})
        )
    ''').columns(datetime=DateTime())
    
    result = db_session.execute(stmt).fetchall()
    return result

def count_annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    stmt = select(func.count()).where(func.ST_Intersects(table.c.centroid, envelope))
    # stmt = table.select([func.count()]).where(func.ST_Intersects(table.c.centroid, envelope))

    result = db_session.execute(stmt).scalar()
    return result

def retrieve_annotation_table(image_id: int, annotation_class_id: int, is_gt: bool) -> Table:
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)

    return Table(table_name, qadb.db.metadata, autoload_with=db_session.bind)

def create_annotation_table(image_id: int, annotation_class_id: int, is_gt: bool):
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt=is_gt)
    table = models.Annotation.__table__.to_metadata(Base.metadata, name=table_name)
    Base.metadata.create_all(bind=db_session.bind, tables=[table])

def delete_all_annotations(image_id: int, annotation_class_id: int, is_gt: bool):
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    model = create_dynamic_model(table_name)
    
    db_session.query(model).delete()

def get_annotation_by_id(image_id: int, annotation_class_id: int, is_gt: bool, annotation_id: int):
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    model = create_dynamic_model(table_name)
    
    return get_annotation_query(model).filter_by(id=annotation_id).first()