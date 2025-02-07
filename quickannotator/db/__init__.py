from geoalchemy2 import load_spatialite
import shapely.wkb as wkb
from sqlalchemy import create_engine, event
from sqlalchemy.orm import column_property, scoped_session, sessionmaker, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

engine = create_engine('sqlite:////opt/QuickAnnotator/quickannotator/instance/quickannotator.db')
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

# Initialize Spatialite extension
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    dbapi_connection.enable_load_extension(True)
    dbapi_connection.execute('SELECT load_extension("mod_spatialite")')
    # dbapi_connection.execute('SELECT InitSpatialMetaData(1);')

def init_db():
    from . import models
    Base.metadata.create_all(bind=engine)

