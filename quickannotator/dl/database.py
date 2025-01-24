import os
import shutil
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from quickannotator.db import db, Image, AnnotationClass, Tile

def get_database_path():
    return "sqlite:////opt/QuickAnnotator/quickannotator/instance/quickannotator.db"

def create_db_engine(db_path):
    engine = create_engine(db_path)
    initialize_spatialite_extension(engine)
    return engine

def initialize_spatialite_extension(engine):
    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        dbapi_connection.enable_load_extension(True)
        dbapi_connection.execute('SELECT load_extension("mod_spatialite")')
        dbapi_connection.execute('SELECT InitSpatialMetaData(1);')

def create_all_tables(engine):
    models = [Image, AnnotationClass, Tile]
    db.metadata.create_all(bind=engine, tables=[item.__table__ for item in models])

def get_session_aj(engine):
    Session = sessionmaker(bind=engine)
    return Session()

def initialize_database():
    db_path = get_database_path()
    engine = create_db_engine(db_path)
    create_all_tables(engine)
    return get_session_aj(engine)

# Initialize the database and get a session
session = initialize_database()
import shutil
from sqlalchemy import create_engine, event, Table
from sqlalchemy.orm import sessionmaker

import shapely.wkb
import numpy as np
import cv2

from sqlalchemy import inspect


from quickannotator.db import db, Project, Image, AnnotationClass, Notification, Tile, Setting, Annotation, SearchCache


