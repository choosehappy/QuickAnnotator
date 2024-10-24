from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Text, Column, Integer, DateTime, ForeignKey, JSON, Boolean, Float, event
from geoalchemy2 import Geometry, load_spatialite
from flask_caching import Cache
from marshmallow import fields
import geojson
from shapely.geometry import mapping
import shapely.wkb as wkb

db = SQLAlchemy()
SearchCache = Cache(config={'CACHE_TYPE': 'SimpleCache'})



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
    id = Column(Integer, primary_key=True)

    # foreign keys
    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    annotation_class_id = Column(Integer, ForeignKey('annotation_class.id'), nullable=False)


    # columns
    geom = Column(Geometry('POLYGON'))
    seen = Column(Integer, nullable=False, default=0)


class Annotation(db.Model):
    """Each table will follow this naming convention: {image_id}_{annotation_class_id}_{gt/pred}"""

    # primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # columns
    centroid = Column(Geometry('POINT'))
    area = Column(Float)
    polygon = Column(Geometry('POLYGON'))
    custom_metrics = Column(JSON)
    datetime = Column(DateTime, server_default=db.func.now())


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
            "description": "A geometry field. Can be WKT or GeoJSON."
        }
        super().__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        # Assuming value is a WKB string
        result = geojson.Feature(geometry=mapping(wkb.loads(str(value.data))))
        return geojson.dumps(result)

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            return None
        # Convert the input into the appropriate geometry type here (WKT, GeoJSON)
        return value
