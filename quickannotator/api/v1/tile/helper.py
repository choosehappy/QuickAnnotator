import quickannotator.db as qadb
from sqlalchemy import func, Table
from quickannotator.db import db
from sqlalchemy.orm import aliased, sessionmaker
from sqlalchemy import exists
import shapely
from shapely.geometry import Polygon
import random
import geojson
from quickannotator.api.v1.annotation.helper import insert_new_annotation
from multiprocessing import Process, current_process
import time

# def tiles_within_bbox_old(db, image_id, annotation_class_id, x1, y1, x2, y2):
#     envelope = func.BuildMbr(x1, y1, x2, y2)

#     tissue_mask_tablename = f"{image_id}_{annotation_class_id}_gt_annotation"
#     tissue_mask_table = Table(tissue_mask_tablename, db.metadata, autoload_with=db.engine)

#     tissue_mask_subquery = (
#         db.session.query(tissue_mask_table.c.polygon)
#         .filter(tissue_mask_table.c.polygon.ST_Intersects(envelope))
#         .subquery()
#     )

#     # Query to get tiles that intersect with any polygon in the tissue mask subquery
#     tiles = db.session.query(qadb.Tile).filter(
#         qadb.Tile.image_id == image_id,
#         qadb.Tile.annotation_class_id == annotation_class_id,
#         qadb.Tile.geom.ST_Intersects(envelope),
#         qadb.Tile.geom.ST_Intersects(tissue_mask_subquery.c.polygon)  # Filter by intersection with tissue mask polygons
#     ).all()

#     return tiles

def tiles_within_bbox(db, image_id, annotation_class_id, x1, y1, x2, y2):
    tm_class_id = 1
    envelope = func.BuildMbr(x1, y1, x2, y2)

    tissue_mask_tablename = f"{image_id}_{tm_class_id}_gt_annotation"
    tissue_mask_table = Table(tissue_mask_tablename, db.metadata, autoload_with=db.engine)
    # Step 1: Define a CTE to pre-filter polygons by the envelope
    envelope_intersecting_polygons = (
        db.session.query(tissue_mask_table.c.polygon)
        .filter(tissue_mask_table.c.polygon.ST_Intersects(envelope))
        .cte("envelope_intersecting_polygons")
    )

    # Step 2: Create an alias for the CTE to use in the main query
    eip_alias = aliased(envelope_intersecting_polygons)

    # Step 3: Main query to filter tiles by intersecting polygons
    tiles = db.session.query(
        *[getattr(qadb.Tile, column.name) for column in qadb.Tile.__table__.columns],
        func.ST_AsGeoJSON(qadb.Tile.geom).label('geom')
    ).filter(
        qadb.Tile.image_id == image_id,
        qadb.Tile.annotation_class_id == annotation_class_id,
        qadb.Tile.geom.ST_Intersects(envelope),
        exists()
        .where(eip_alias.c.polygon.ST_Intersects(qadb.Tile.geom))
    ).all()

    return tiles

def tile_by_id(session, tile_id: int) -> qadb.Tile:
    result = session.query(qadb.Tile).filter(qadb.Tile.id == tile_id).first()
    return result

def generate_random_circle_within_bbox(bbox: Polygon, radius: float) -> shapely.geometry.Polygon:
    minx, miny, maxx, maxy = bbox.bounds
    x = minx + (maxx - minx) * random.random()
    y = miny + (maxy - miny) * random.random()

    circle = shapely.geometry.Point(x, y).buffer(radius)
    intersection = bbox.intersection(circle)
    return intersection

def compute_on_tile(db, qadb, tile_id: int, sleep_time=5): 
    def async_task():
        Session = sessionmaker(bind=db.engine)

        time.sleep(sleep_time)

        with Session() as session:
            tile = tile_by_id(session, tile_id)
            image_id: int = tile.image_id
            annotation_class_id: int = tile.annotation_class_id

            bbox = shapely.wkb.loads(tile.geom.data)
            for i in range(random.randint(20, 40)):
                polygon = generate_random_circle_within_bbox(bbox, 100)
                insert_new_annotation(session, image_id, annotation_class_id, is_gt=False, polygon=polygon)

            # now that the tile has been processed, update the tile.seen column to 2
            tile.seen = 2
            session.commit()

        print(f"Async task completed by process id: {current_process().pid}")
        print(f"Generated polygon: {polygon}")

    process = Process(target=async_task)
    process.start()
    return process.pid


def reset_all_tiles_seen(db):
    """
    Resets the 'seen' status of all tiles in the database to 0.
    Args:
        db: The database session object used to interact with the database.
    Returns:
        None
    """

    db.session.query(qadb.Tile).update({qadb.Tile.seen: 0})
    db.session.commit()