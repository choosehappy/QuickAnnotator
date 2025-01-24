import quickannotator.db as qadb
from sqlalchemy import func, Table
from quickannotator.db import db
from sqlalchemy.orm import aliased, sessionmaker, Session
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
import math
from sqlalchemy.dialects.sqlite import insert   # NOTE: This import is necessary as there is no dialect-neutral way to call on_conflict()


def get_tile(session: Session, annotation_class_id: int, image_id: int, tile_id: int) -> qadb.Tile:
    result = session.query(qadb.Tile).filter_by(
        annotation_class_id=annotation_class_id,
        image_id=image_id,
        tile_id=tile_id
    ).first()
    return result

def upsert_tile(annotation_class_id: int, image_id: int, tile_id: int, seen: int=None, hasgt: bool=None):
    '''
        Inserts a new tile record into the database or updates an existing one based on the given parameters.
        The function uses an upsert operation to either insert a new record or update an existing one
        based on the combination of `annotation_class_id`, `image_id`, and `tile_id`.
        Parameters:
        - session (Session): The database session to use for the operation.
        - annotation_class_id (int): The ID of the annotation class.
        - image_id (int): The ID of the image.
        - tile_id (int): The ID of the tile.
        - seen (int): The seen status of the tile.
        - hasgt (bool): A flag indicating whether the tile is ground truth (True) or not (False).
        Returns:
        - result: The result of the executed statement.
    '''
    update_fields = {}
    if seen is not None:    # Only update the 'seen' field if the value is provided
        update_fields['seen'] = seen
    if hasgt is not None:   # Only update the 'hasgt' field if the value is provided
        update_fields['hasgt'] = hasgt
    
    stmt = insert(qadb.Tile).values(
        annotation_class_id=annotation_class_id,
        image_id=image_id,
        tile_id=tile_id,
        **update_fields
    ).on_conflict_do_update(
        index_elements=['annotation_class_id', 'image_id', 'tile_id'],
        set_=update_fields
    )
    
    result = qadb.db.session.execute(stmt)
    qadb.db.session.commit()
    
    return result
    

def get_tile_ids_within_bbox(tile_size: int, bbox: tuple, image_width: int, image_height: int) -> list:
    # Bounding box: (x1, y1, x2, y2)
    x1, y1, x2, y2 = bbox

    # Verify that the bounding box is within the image dimensions
    if not (x1 < x2 and y1 < y2):
        raise ValueError(f"Bounding box coordinates must be monotonically increasing: {bbox}")
    if not (0 <= x1 < x2 <= image_width and 0 <= y1 < y2 <= image_height):
        raise ValueError(f"Bounding box {bbox} is out of image dimensions (0, 0, {image_width}, {image_height})")

    # Calculate the number of tiles per row
    tiles_per_row = math.ceil(image_width / tile_size)

    # Determine the tile range
    start_col = x1 // tile_size
    end_col = math.ceil(x2 / tile_size) - 1
    start_row = y1 // tile_size
    end_row = math.ceil(y2 / tile_size) - 1
    
    # Collect tile IDs
    tile_ids = []
    for row in range(start_row, end_row + 1):
        for col in range(start_col, end_col + 1):
            tile_id = row * tiles_per_row + col

            tile_ids.append(tile_id)
    
    return tile_ids

def get_tile_id_for_point(tile_size: int, point: tuple, grid_width: int, grid_height) -> int:
    if not (0 <= point[0] < grid_width and 0 <= point[1] < grid_height):
        raise ValueError(f"Point {point} is out of image dimensions (0, 0, {grid_width}, {grid_height})")

    x, y = point
    col = x // tile_size
    row = y // tile_size
    tile_id = row * (grid_width // tile_size) + col
    return tile_id

def generate_random_circle_within_bbox(bbox: Polygon, radius: float) -> shapely.geometry.Polygon:
    minx, miny, maxx, maxy = bbox.bounds
    x = minx + (maxx - minx) * random.random()
    y = miny + (maxy - miny) * random.random()

    circle = shapely.geometry.Point(x, y).buffer(radius)
    intersection = bbox.intersection(circle)
    return intersection

@ray.remote
def remote_compute_on_tile(db_url, annotation_class_id: int, image_id: int, tile_id: int, sleep_time=5):
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
            tile = get_tile(session, annotation_class_id, image_id, tile_id)  # Replace with your actual function to get the tile
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


def compute_on_tile(db, annotation_class_id: int, image_id: int, tile_id: int, sleep_time=5):
    db_url = db.engine.url
    ref = remote_compute_on_tile.remote(str(db_url), annotation_class_id, image_id, tile_id, sleep_time)
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