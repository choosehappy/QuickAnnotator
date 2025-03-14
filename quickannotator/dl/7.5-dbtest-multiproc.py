# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

import random
import multiprocessing
import time
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import NoResultFound


# +
#---- this seems to work!
import datetime
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql import text

from sqlalchemy import Index


# --- Setup the SQLite database & SQLAlchemy ORM ---

# Using a file-based SQLite database and allow multithreaded access:
#engine = create_engine("sqlite:///test1.db", connect_args={"check_same_thread": False})
engine = create_engine('postgresql://postgres@localhost:5333/ajtest2')
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class Tile(Base):
    __tablename__ = 'tiles'
    id = Column(Integer, primary_key=True)
    annotation_class_id = Column(Integer, default=1)  # for demo, all tiles use 1
    hasgt = Column(Boolean, default=True)
    datetime = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="pending")  # can be "pending", "in_progress", etc.
    worker_id = Column(Integer, nullable=True)    # which worker claimed it

    # Correct way to define indexes
    __table_args__ = (
        Index("idx_datetime", datetime),
        Index("idx_status", status),
    )



# --- Utility to get a session ---
@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()



# +
from sqlalchemy.orm import Session
from sqlalchemy import update, select, text
from sqlalchemy.engine import Engine

def getWorkersTile(worker_id: int):
    """
    Atomically retrieves and marks a tile as 'in_progress' so no two workers claim the same tile.
    """

    engine = create_engine('postgresql://user:password@localhost/dbname')  # Replace with your database URL
    Session = sessionmaker(bind=engine)
    
    with get_session() as db_session:  # Ensure this provides a session context
        dialect = db_session.bind.dialect.name  # Get database type
        with db_session.begin():  # Explicit transaction
            subquery = (
                select(Tile.id)
                .where(Tile.annotation_class_id == 1,
                       Tile.hasgt == True,
                       Tile.status == 'pending')
                .order_by(Tile.datetime.desc())
                .limit(1).with_for_update(skip_locked=True)
            )
            
            tile = db_session.execute(
                update(Tile)
                .where(Tile.id == subquery.scalar_subquery())
                .where(Tile.status == 'pending')  # Ensures another worker hasn't claimed it
                .values(status='in_progress', worker_id=worker_id)
                .returning(Tile)
            ).scalar()
            
            if tile:
                return f"Worker {worker_id} claimed Tile {tile.id}"
            else:
                return f"Worker {worker_id} found no tile"
 

# -

# --- Worker function ---
def worker_function(worker_id):
    result = getWorkersTile(worker_id)
    print(result)
    return result


# +
from concurrent.futures import ProcessPoolExecutor, as_completed

# --- Main function: spawn many workers concurrently using multiprocessing ---
def main():
    num_workers = 2  # simulate an aggressive scenario with 200 concurrent workers
    results = []
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker_function, worker_id) for worker_id in range(num_workers)]
        print("done starting")
        for future in as_completed(futures):
            results.append(future.result())
    
    print("\nSummary:")
    claimed = [r for r in results if "claimed Tile" in r]
    for res in results:
        print(res)
    print(f"\nTotal claimed tiles: {len(claimed)}")

if __name__ == "__main__":

    # Drop and recreate the table (for demo purposes)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # -
    
    Tile.__table__.indexes
    
    # --- Populate the database with some tiles ---
    with SessionLocal() as session:
        tiles = []
        for i in range(100_000):  # create tiles
            tile = Tile(
                annotation_class_id=1,
                hasgt=True,
                # Newer tiles have a more recent datetime:
                datetime=datetime.datetime.utcnow() - datetime.timedelta(seconds=i)
            )
            tiles.append(tile)
        session.add_all(tiles)
        session.commit()
    
    main()


# +
# # --- Main function: spawn many workers concurrently ---
# def main():
#     num_workers = 200  # simulate an aggressive scenario with 200 concurrent workers
#     results = []
#     with ThreadPoolExecutor(max_workers=num_workers) as executor:
#         futures = [executor.submit(worker_function, worker_id) for worker_id in range(num_workers)]
#         for future in as_completed(futures):
#             results.append(future.result())
    
#     print("\nSummary:")
#     claimed = [r for r in results if "claimed Tile" in r]
#     for res in results:
#         print(res)
#     print(f"\nTotal claimed tiles: {len(claimed)}")

# if __name__ == "__main__":
#     main()

# +

result = getWorkersTile(-1)
# -

result


