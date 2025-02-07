from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import load_spatialite
import shapely.wkb as wkb
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import column_property
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()

Base = declarative_base()

