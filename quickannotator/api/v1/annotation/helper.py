import quickannotator.db as qadb
from sqlalchemy import func, select
import quickannotator.db as qadb
import shapely.geometry

def annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    # Right now we are selecting by centroid and not polygon.
    stmt = table.select().where(func.ST_Intersects(table.c.centroid, envelope))
    result = qadb.db.session.execute(stmt).fetchall()
    return result

def count_annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    stmt = select(func.count()).where(func.ST_Intersects(table.c.centroid, envelope))
    # stmt = table.select([func.count()]).where(func.ST_Intersects(table.c.centroid, envelope))

    result = qadb.db.session.execute(stmt).scalar()
    return result
