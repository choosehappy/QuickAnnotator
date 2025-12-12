from typing import List
from geoalchemy2 import Geometry
import geojson.geometry
from marshmallow import fields
from sqlalchemy.sql import func
from quickannotator.db import Base
from sqlalchemy.orm import relationship
import geojson
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, Text, func, ext
from ..constants import TileStatus
from sqlalchemy import Enum
from datetime import datetime
from sqlalchemy.ext.declarative import DeclarativeMeta


log_level_enum = Enum('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', name='log_level_enum')


class Project(Base):
    """
    The projects table will store all the projects created by the user.
    """
    __tablename__ = 'project'
    # primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # columns
    name = Column(Text, nullable=False, unique=True)

    description = Column(Text, default="")
    # is_dataset_large project setting that currently has no use.
    # a "large" dataset might have e.g., > 100 million total histologic object annotations
    is_dataset_large = Column(Boolean, default=False)   
    datetime = Column(DateTime, default=datetime.now)

    # relationships
    images = relationship('Image', backref='project', lazy=True)
    annotation_classes = relationship('AnnotationClass', backref='project', lazy=True)
    settings = relationship("Setting", backref='project', lazy=True)
    notifications = relationship("Notification", backref='project', lazy=True)


class Image(Base):
    __tablename__ = 'image'
    # primary
    id = Column(Integer, primary_key=True, autoincrement=True)

    # foreign keys
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)

    # columns
    name = Column(Text, nullable=False)
    path = Column(Text)
    base_height = Column(Integer)
    base_width = Column(Integer)
    base_mag = Column(Float)
    dz_tilesize = Column(Integer)
    embedding_coord = Column(Geometry('POINT'))
    group_id = Column(Integer)
    split = Column(Integer)
    datetime = Column(DateTime, default=datetime.now)

    # relationships
    notifications = relationship("Notification", backref='image', lazy=True)


class AnnotationClass(Base):
    __tablename__ = 'annotation_class'
    # primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # foreign keys
    project_id = Column(Integer, ForeignKey('project.id'), nullable=True)

    # columns
    name = Column(Text, nullable=False, unique=True)
    color = Column(Text, nullable=False)
    work_mag = Column(Float, nullable=False)
    work_tilesize = Column(Integer, nullable=False)
    datetime = Column(DateTime, default=datetime.now)


class Tile(Base):
    __tablename__ = 'tile'
    # primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # foreign keys
    annotation_class_id = Column(Integer, ForeignKey('annotation_class.id'), nullable=False)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    tile_id = Column(Integer, nullable=False)

    # columns
    pred_status = Column(Integer, nullable=False, default=TileStatus.UNSEEN)
    pred_datetime = Column(DateTime, nullable=True, default=None)

    gt_counter = Column(Integer, nullable=True, default=None)
    gt_datetime = Column(DateTime, nullable=True, default=None)

    # relationships
    image = relationship('Image', backref='tiles')
    annotation_class = relationship('AnnotationClass', backref='tiles')

    # indexes
    __table_args__ = (
        Index('idx_annotation_class_image_tile', 'annotation_class_id', 'image_id', 'tile_id', unique=True),
        Index('idx_gt', gt_counter,gt_datetime),        #maybe these should be the other way around? e.g., date then counter? #these are being queried ascending -- leave as is
        Index('idx_pred',pred_status, pred_datetime.desc())  #looks like date time is queried descending, inverting index
    )


class Annotation(Base):
    """Each table will follow this naming convention: annotation_{image_id}_{annotation_class_id}_{gt/pred}"""

    __tablename__ = 'annotation'
    # primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # These columns are kept null intentionally because the information is stored in the table name. Consider eventually removing these columns.
    # image_id = Column(Integer, nullable=True, default=None)
    # annotation_class_id = Column(Integer, nullable=True, default=None)
    # isgt = Column(Boolean, nullable=True, default=None)

    # columns
    tile_id = Column(Integer, nullable=False, default=None)
    centroid = Column(Geometry('POINT', srid=0))  # Stored as geometry
    area = Column(Float)
    polygon = Column(Geometry('POLYGON', srid=0))  # Stored as geometry
    custom_metrics = Column(JSON)
    datetime = Column(DateTime, default=datetime.now)


class Notification(Base):

    __tablename__ = 'notification'
    # primary key
    id = Column(Integer, primary_key=True)

    # foreign keys
    project_id = Column(Integer, ForeignKey('project.id'), nullable=True)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=True)

    # columns
    message_type = Column(Integer, nullable=False)
    is_read = Column(Boolean, nullable=False)
    message = Column(Text, nullable=False)
    datetime = Column(DateTime, default=datetime.now)


class Log(Base):

    __tablename__ = 'log'

    # primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # columns
    name = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    level = Column(log_level_enum, nullable=False, default='INFO')
    message = Column(Text, nullable=False, default="")


class Setting(Base):
    """
    The settings table will store all project-level and application-level settings.
    """

    __tablename__ = 'setting'
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
        return value

    def _deserialize(self, value, attr, data, **kwargs) -> geojson.geometry.Geometry:
        try:
            geom = geojson.loads(value) # NOTE: potentially optimize using orjson.loads
            return geom
        except Exception as e:
            raise ValueError(f"Invalid geometry format: {e}")


def get_model_column_names(model: DeclarativeMeta) -> List[str]:
    """
    Returns a list of column names for the given SQLAlchemy model.
    Args:
        model (Base): The SQLAlchemy model class.
    Returns:
        List[str]: A list of column names.
    """
    return [getattr(model, column.name) for column in model.__table__.columns]