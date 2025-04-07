import shapely.wkb as wkb
from sqlalchemy import create_engine, event
from sqlalchemy.orm import column_property, scoped_session, sessionmaker, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from contextlib import contextmanager
from quickannotator.config import get_database_uri
import geoalchemy2

engine = create_engine(get_database_uri())
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

geoalchemy2.admin.dialects.sqlite.register_sqlite_mapping(
    {"ST_Scale": "ScaleCoords"}
)

Base = declarative_base()
Base.query = db_session.query_property()

# Initialize Spatialite extension only if the database is SQLite
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        dbapi_connection.enable_load_extension(True)
        dbapi_connection.execute('SELECT load_extension("mod_spatialite")')
        dbapi_connection.execute('SELECT InitSpatialMetaData(1);')

def init_db():
    from . import models
    # Exclude model.Annotation from table creation
    tables = [table for table in Base.metadata.tables.values() if table.name != 'annotation']
    Base.metadata.create_all(bind=engine, tables=tables)

def drop_db():
    # Drop all tables in the database
    Base.metadata.drop_all(bind=engine)

@contextmanager
def get_session():
    """Provides a transactional scope for db_session outside Flask."""
    try:
        yield db_session  # Use db_session just like in Flask
        db_session.commit()  # Auto-commit after block exits
    except Exception as e:
        db_session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db_session.remove()  # Cleanup session automatically
        #print("Session closed")
