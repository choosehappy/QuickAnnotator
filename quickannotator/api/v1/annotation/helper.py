import quickannotator.db as qadb
from sqlalchemy import func, select, text, MetaData, Table
from sqlalchemy.orm import aliased, Session
from typing import List
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import DateTime
from quickannotator.db import create_dynamic_model, build_annotation_table_name, Annotation

Base = declarative_base()

def annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    # Right now we are selecting by centroid and not polygon.
    stmt = table.select().where(func.ST_Intersects(table.c.centroid, envelope))
    result = qadb.db.session.execute(stmt).fetchall()
    return result

def get_annotations_for_tile(image_id: int, annotation_class_id: int, tile_id: int, is_gt: bool) -> List[dict]:
    model: Annotation = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, is_gt))
    result = qadb.db.session.query(
        func.AsGeoJSON(model.centroid).label('centroid'),
        model.area,
        func.AsGeoJSON(model.polygon).label('polygon'),
        model.custom_metrics,
        model.datetime,
        model.annotation_class_id,
        model.tile_id
    ).filter_by(tile_id=tile_id).all()
    
    return result

def annotations_within_bbox_spatial(table_name: str, x1: float, y1: float, x2: float, y2: float) -> List[qadb.Annotation]:
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
    
    result = qadb.db.session.execute(stmt).fetchall()
    return result

def count_annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    stmt = select(func.count()).where(func.ST_Intersects(table.c.centroid, envelope))
    # stmt = table.select([func.count()]).where(func.ST_Intersects(table.c.centroid, envelope))

    result = qadb.db.session.execute(stmt).scalar()
    return result

def retrieve_annotation_table(session, image_id: int, annotation_class_id: int, is_gt: bool) -> Table:
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)

    return Table(table_name, qadb.db.metadata, autoload_with=session.bind)

def delete_all_annotations(session, image_id: int, annotation_class_id: int, is_gt: bool):
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    model = create_dynamic_model(table_name)
    
    session.query(model).delete()
    session.commit()