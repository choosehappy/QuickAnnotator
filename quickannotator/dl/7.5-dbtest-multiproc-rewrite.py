import random
import multiprocessing
import time
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql import text, select, update
from contextlib import contextmanager
import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed


# --- Setup the PostgreSQL database & SQLAlchemy ORM ---
DATABASE_URL = 'postgresql://postgres@localhost:5333/ajtest1'
#DATABASE_URL = "sqlite:///test1a.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Tile(Base):
    __tablename__ = 'tiles'
    id = Column(Integer, primary_key=True)
    annotation_class_id = Column(Integer, default=1)
    hasgt = Column(Boolean, default=True)
    datetime = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="pending")
    worker_id = Column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_datetime", datetime),
        Index("idx_status", status),
    )

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



def getWorkersTiles(worker_id: int):
    with get_session() as db_session:  # Ensure this provides a session context
        with db_session.begin():  # Explicit transaction
            subquery = (
                select(Tile.id)
                .where(Tile.annotation_class_id == 1,
                    Tile.hasgt == True,
                    Tile.status == 'pending')
                .order_by(Tile.datetime.desc()) #always get the latest ones first
                .limit(1).with_for_update(skip_locked=True) #with_for_update is a Postgres specific clause
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
    
    ## --- if one needs just the ID this will work - might be a *touch* faster, but i suspect its not significant
    #         tile = db_session.execute(
    #             update(Tile)
    #             .where(Tile.id == subquery.scalar_subquery())
    #             .where(Tile.status == 'pending')  # Ensures another worker hasn't claimed it
    #             .values(status='done')
    #             .returning(Tile.id)
    #         ).scalar()
            
    # if tile:
    #     return f"Worker {worker_id} claimed Tile {tile}"
    # else:
    #     return f"Worker {worker_id} found no tile"


def worker_function(worker_id):
    result = getWorkersTiles(worker_id)
    print(result)
    return result

def main():
    print("Starting main")
    num_workers = 50
    results = []
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker_function, worker_id) for worker_id in range(num_workers)]
        for future in as_completed(futures):
            results.append(future.result())

    print("\nSummary:")
    claimed = [r for r in results if "claimed Tile" in r]
    for res in results:
        print(res)
    print(f"\nTotal claimed tiles: {len(claimed)}")

if __name__ == "__main__":
    "starting creation"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        tiles = []
        for i in range(10_000):
            tile = Tile(
                annotation_class_id=1,
                hasgt=True,
                datetime=datetime.datetime.utcnow() - datetime.timedelta(seconds=i)
            )
            tiles.append(tile)
        session.add_all(tiles)
        session.commit()
    print("Starting main 2")
    main()