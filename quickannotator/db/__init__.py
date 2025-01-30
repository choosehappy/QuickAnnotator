from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Text, Column, Integer, DateTime, ForeignKey, JSON, Boolean, Float, event, Index, Table
from geoalchemy2 import Geometry, load_spatialite
from marshmallow import fields
import geojson
import shapely.wkb as wkb
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import column_property
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()

Base = declarative_base()

def create_dynamic_model(table_name, base=Base):
    class DynamicAnnotation(base):
        __tablename__ = table_name
        __table__ = Table(table_name, base.metadata, autoload_with=db.engine)

    return DynamicAnnotation

class Project(db.Model):
    """
    The projects table will store all the projects created by the user.
    """
    # primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # columns
    name = Column(Text, nullable=False, unique=True)

    description = Column(Text, default="")
    is_dataset_large = Column(Boolean, default=False)
    datetime = Column(DateTime, server_default=db.func.now())

    # relationships
    images = db.relationship('Image', backref='project', lazy=True)
    annotation_classes = db.relationship('AnnotationClass', backref='project', lazy=True)
    settings = db.relationship("Setting", backref='project', lazy=True)
    notifications = db.relationship("Notification", backref='project', lazy=True)


class Image(db.Model):
    # primary
    id = Column(Integer, primary_key=True, autoincrement=True)

    # foreign keys
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)

    # columns
    name = Column(Text, nullable=False)
    path = Column(Text)
    height = Column(Integer)
    width = Column(Integer)
    dz_tilesize = Column(Integer)
    embedding_coord = Column(Geometry('POINT'))
    group_id = Column(Integer)
    split = Column(Integer)
    datetime = Column(DateTime, server_default=db.func.now())

    # relationships
    notifications = db.relationship("Notification", backref='image', lazy=True)
    tile = db.relationship('Tile', backref='image', lazy=True)


class AnnotationClass(db.Model):
    # primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # foreign keys
    project_id = Column(Integer, ForeignKey('project.id'), nullable=True)

    # columns
    name = Column(Text, nullable=False, unique=True)
    color = Column(Text, nullable=False)
    magnification = Column(Integer, nullable=True)
    patchsize = Column(Integer, nullable=True)
    tilesize = Column(Integer, nullable=True)
    dl_model_objectref = Column(Text, nullable=True)
    datetime = Column(DateTime, server_default=db.func.now())

    # relationships
    db.relationship("Tile", backref='annotation_class', lazy=True)


class Tile(db.Model):
    # primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # foreign keys
    annotation_class_id = Column(Integer, ForeignKey('annotation_class.id'), nullable=False)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    tile_id = Column(Integer, nullable=False)

    # columns
    seen = Column(Integer, nullable=False, default=0)
    hasgt = Column(Boolean, nullable=False, default=False)
    datetime = Column(DateTime, server_default=db.func.now())

    # indexes
    __table_args__ = (
        Index('idx_annotation_class_image_tile', 'annotation_class_id', 'image_id', 'tile_id', unique=True),
    )
    

class Annotation(db.Model):
    """Each table will follow this naming convention: annotation_{image_id}_{annotation_class_id}_{gt/pred}"""

    # primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # foreign keys (redundant due to table naming but useful for queries and future proofing)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=True, default=None)
    annotation_class_id = Column(Integer, ForeignKey('annotation_class.id'), nullable=True, default=None)
    tile_id = Column(Integer, ForeignKey('tile.tile_id'), nullable=True, default=None)

    # columns
    isgt = Column(Boolean, nullable=True, default=None)
    centroid = Column(Geometry('POINT', srid=4326))  # Stored as geometry
    area = Column(Float)
    polygon = Column(Geometry('POLYGON', srid=4326))  # Stored as geometry
    custom_metrics = Column(JSON)
    datetime = Column(DateTime, server_default=func.now())
    

def build_annotation_table_name(image_id: int, annotation_class_id: int, is_gt: bool):
    gtpred = 'gt' if is_gt else 'pred'
    table_name = f"annotation_{image_id}_{annotation_class_id}_{gtpred}"
    return table_name

class Notification(db.Model):
    # primary key
    id = Column(Integer, primary_key=True)

    # foreign keys
    project_id = Column(Integer, ForeignKey('project.id'), nullable=True)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=True)

    # columns
    message_type = Column(Integer, nullable=False)
    is_read = Column(Boolean, nullable=False)
    message = Column(Text, nullable=False)
    datetime = Column(DateTime, server_default=db.func.now())

class Setting(db.Model):
    """
    The settings table will store all project-level and application-level settings.
    """

    # primary key
    id = Column(Integer, primary_key=True)

    # foreign keys
    project_id = Column(Integer, ForeignKey('project.id'), nullable=True)

    # columns
    name = Column(Text, nullable=False)
    value = Column(Text)
    description = Column(Text)
    default_value = Column(Text)

class GeometryField(fields.Field):
    def __init__(self, *args, **kwargs):
        # Pass metadata information to describe the field for Swagger
        kwargs["metadata"] = {
            "type": "string",  # You can also specify "object" if it's GeoJSON
            "description": "A geometry field. Serialized WKB into geojson."
        }
        super().__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        # if isinstance(value, str):
        #     return geojson.loads(value)
        return value

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            geom = geojson.loads(value)
            return geom
        except Exception as e:
            raise ValueError(f"Invalid geometry format: {e}")
