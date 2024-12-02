import quickannotator.db as qadb
from sqlalchemy import func, select, text, MetaData, Table
from sqlalchemy.orm import aliased
from typing import List
import quickannotator.db as qadb
import shapely.geometry
from sqlalchemy.ext.declarative import declarative_base
import time

Base = declarative_base()

def get_or_create_model_for_table(table_name: str, metadata, engine):
    table = Table(table_name, metadata, autoload_with=engine)
    class DynamicModel(Base):
        __table__ = table
    return DynamicModel

def annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    # Right now we are selecting by centroid and not polygon.
    stmt = table.select().where(func.ST_Intersects(table.c.centroid, envelope))
    result = qadb.db.session.execute(stmt).fetchall()
    return result

def annotations_within_bbox_spatial_old(table_name: str, x1: float, y1: float, x2: float, y2: float) -> List[qadb.Annotation]:
    stmt = text(f'''
        SELECT ROWID, AsEWKB(centroid) as centroid, area, AsEWKB(polygon) as polygon, custom_metrics, datetime
        FROM "{table_name}"
        WHERE "{table_name}".ROWID IN (
            SELECT ROWID
            FROM SpatialIndex
            WHERE f_table_name = "{table_name}"
            AND f_geometry_column = 'centroid'
            AND search_frame = BuildMbr({x1}, {y1}, {x2}, {y2})
        )
    ''')
    
    result = qadb.db.session.execute(stmt).fetchall()
    return result

def annotations_within_bbox_spatial(table_name: str, x1: float, y1: float, x2: float, y2: float) -> List[qadb.Annotation]:
    model = get_or_create_model_for_table(table_name, qadb.db.metadata, qadb.db.engine)
    
    # Subquery for the spatial index filtering
    spatial_subquery = text(f'''
        SELECT ROWID
        FROM SpatialIndex
        WHERE f_table_name = '{table_name}'
        AND f_geometry_column = 'centroid'
        AND search_frame = BuildMbr({x1}, {y1}, {x2}, {y2})
    ''')
    
    # Main query using the spatial subquery
    query = (
        select(model)
        .where(model.id.in_(spatial_subquery))
    )
    
    start_time = time.time()
    result = qadb.db.session.execute(query).scalars().all()  # `.scalars()` maps to the ORM model
    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")
    return result

def count_annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    stmt = select(func.count()).where(func.ST_Intersects(table.c.centroid, envelope))
    # stmt = table.select([func.count()]).where(func.ST_Intersects(table.c.centroid, envelope))

    result = qadb.db.session.execute(stmt).scalar()
    return result
