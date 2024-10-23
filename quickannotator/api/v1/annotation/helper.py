import quickannotator.db as qadb
from sqlalchemy import func
import quickannotator.db as qadb
import shapely.geometry

def annotations_within_bbox(table, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)
    # Right now we are selecting by centroid and not polygon.
    stmt = table.select().where(func.ST_Intersects(table.c.centroid, envelope))

    result = qadb.db.session.execute(stmt).fetchall()
    return result

# def annotations_within_polygon(db, image_id, annotation_class_id, polygon):
#     envelope = func.ST_Envelope(polygon)
#
#     tiles = db.session.query(qadb.Tile).filter(
#         qadb.Tile.image_id == image_id,
#         qadb.Tile.annotation_class_id == annotation_class_id,
#         qadb.Tile.geom.ST_Within(envelope)
#     ).all()