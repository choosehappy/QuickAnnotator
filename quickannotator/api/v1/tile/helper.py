import quickannotator.db as qadb
from sqlalchemy import func, Table
from quickannotator.db import db
from sqlalchemy.orm import aliased, sessionmaker
from sqlalchemy import exists, event
import shapely
from shapely.geometry import Polygon
import random
import geojson
from quickannotator.api.v1.annotation.helper import insert_new_annotation
from multiprocessing import Process, current_process
import time
import ray
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def tiles_within_bbox(db, image_id, annotation_class_id, x1, y1, x2, y2):
    tm_class_id = 1
    envelope = func.BuildMbr(x1, y1, x2, y2)

    tissue_mask_tablename = f"{image_id}_{tm_class_id}_gt_annotation"
    tissue_mask_table = Table(tissue_mask_tablename, db.metadata, autoload_with=db.engine)

    # Main query to filter tiles by intersecting polygons without pre-filtering
    tiles = db.session.query(
        *[getattr(qadb.Tile, column.name) for column in qadb.Tile.__table__.columns],
        func.ST_AsGeoJSON(qadb.Tile.geom).label('geom')
    ).filter(
        qadb.Tile.image_id == image_id,
        qadb.Tile.annotation_class_id == annotation_class_id,
        qadb.Tile.geom.ST_Intersects(envelope),
        exists()
        .where(tissue_mask_table.c.polygon.ST_Intersects(qadb.Tile.geom))
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

@ray.remote
def remote_compute_on_tile(db_url, tile_id: int, sleep_time=5):
    time.sleep(sleep_time)
    # Create the engine and session for each Ray task
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    # Attach the event listener to the engine (inside the task to ensure it's unique per task)
    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        try:
            # Enable the Spatialite extension on the raw SQLite connection
            if hasattr(dbapi_connection, "enable_load_extension"):
                dbapi_connection.enable_load_extension(True)
                dbapi_connection.execute('SELECT load_extension("mod_spatialite")')
                dbapi_connection.execute("PRAGMA busy_timeout=10000000;")
                print("Spatialite extension loaded successfully")
            else:
                print("Extension loading not supported for this connection")
        except Exception as e:
            print(f"Error enabling Spatialite extension: {e}")

    try:
        # Start a session for the task
        with Session() as session:
            # Example: load the tile and process
            tile = tile_by_id(session, tile_id)  # Replace with your actual function to get the tile
            image_id: int = tile.image_id
            annotation_class_id: int = tile.annotation_class_id

            # Process the tile (using shapely for example)
            bbox = shapely.wkb.loads(tile.geom.data)
            for _ in range(random.randint(20, 40)):
                polygon = generate_random_circle_within_bbox(bbox, 100)
                insert_new_annotation(session, image_id, annotation_class_id, is_gt=False, polygon=polygon)

            # Mark tile as processed
            tile.seen = 2
            
            session.commit()

    except Exception as e:
        print(f"Error processing tile: {e}")

    finally:
        # Cleanup: Dispose of the engine when the task is done
        engine.dispose()


def compute_on_tile(db, qadb, tile_id: int, sleep_time=5):
    db_url = db.engine.url
    ref = remote_compute_on_tile.remote(str(db_url), tile_id, sleep_time)
    return ref.hex()


def reset_all_tiles_seen(session):
    """
    Resets the 'seen' status of all tiles in the database to 0.
    Args:
        db: The database session object used to interact with the database.
    Returns:
        None
    """

    session.query(qadb.Tile).update({qadb.Tile.seen: 0})
    session.commit()