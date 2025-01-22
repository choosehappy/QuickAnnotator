import quickannotator.db as qadb
from sqlalchemy import func, select, text, MetaData, Table
from sqlalchemy.orm import aliased, Session
from typing import List
import quickannotator.db as qadb
import shapely.geometry
from sqlalchemy.ext.declarative import declarative_base
import time
from sqlalchemy.types import DateTime
from datetime import datetime
import json
import random
from quickannotator.db import create_dynamic_model, build_annotation_table_name

Base = declarative_base()

def annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    # Right now we are selecting by centroid and not polygon.
    stmt = table.select().where(func.ST_Intersects(table.c.centroid, envelope))
    result = qadb.db.session.execute(stmt).fetchall()
    return result

def get_annotations_for_tile(session: Session, image_id, annotation_class_id, tile_id) -> List[qadb.Annotation]:
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt=True)
    model = create_dynamic_model(table_name)
    result = session.query(model).filter_by(tile_id=tile_id).all()
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

# def annotations_within_bbox_spatial_new(table_name: str, x1: float, y1: float, x2: float, y2: float) -> List[qadb.Annotation]:
#     model = get_or_create_model_for_table(table_name, qadb.db.metadata, qadb.db.engine)
    
#     # Subquery for the spatial index filtering
#     spatial_subquery = text(f'''
#         SELECT ROWID
#         FROM SpatialIndex
#         WHERE f_table_name = '{table_name}'
#         AND f_geometry_column = 'centroid'
#         AND search_frame = BuildMbr({x1}, {y1}, {x2}, {y2})
#     ''')
    
#     # Main query using the spatial subquery
#     query = (
#         select(
#             model.id,
#             func.AsGeoJSON(model.centroid).label('centroid'),
#             model.area,
#             func.AsGeoJSON(model.polygon).label('polygon'),
#             model.custom_metrics,
#             model.datetime
#         )
#         .where(model.id.in_(spatial_subquery))
#     )
    
#     start_time = time.time()
#     result = qadb.db.session.execute(query).scalars().all()  # `.scalars()` maps to the ORM model
#     end_time = time.time()
#     print(f"Execution time: {end_time - start_time} seconds")
#     return result

def count_annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    stmt = select(func.count()).where(func.ST_Intersects(table.c.centroid, envelope))
    # stmt = table.select([func.count()]).where(func.ST_Intersects(table.c.centroid, envelope))

    result = qadb.db.session.execute(stmt).scalar()
    return result

def retrieve_annotation_table(session, image_id: int, annotation_class_id: int, is_gt: bool) -> Table:
    gtpred = 'gt' if is_gt else 'pred'
    table_name = f"{image_id}_{annotation_class_id}_{gtpred}_annotation"

    return Table(table_name, qadb.db.metadata, autoload_with=session.bind)

def compute_custom_metrics() -> dict:
    return json.dumps({"iou": 0.5})

def annotation_by_id(table, annotation_id):
    stmt = table.select().where(table.c.id == annotation_id).with_only_columns(
        *(col for col in table.c if col.name != "polygon" and col.name != "centroid"),
        table.c.centroid.ST_AsGeoJSON().label('centroid'),
        table.c.polygon.ST_AsGeoJSON().label('polygon')
    )
    result = qadb.db.session.execute(stmt).first()

    return result

def insert_new_annotation(session, image_id, annotation_class_id, is_gt, polygon: shapely.geometry.Polygon):
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    model = create_dynamic_model(table_name)

    new_annotation = model(
        image_id=image_id,
        annotation_class_id=annotation_class_id,
        isgt=is_gt,
        centroid=polygon.centroid.wkt,
        area=polygon.area,
        polygon=polygon.wkt,
        custom_metrics=compute_custom_metrics(),
        datetime=datetime.now()
    )
    session.add(new_annotation)

def delete_all_annotations(session, image_id: int, annotation_class_id: int, is_gt: bool):
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    model = create_dynamic_model(table_name)
    
    session.query(model).delete()
    session.commit()