from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Text, Column, Integer, DateTime, ForeignKey, JSON, Boolean
from geoalchemy2 import Geometry

db = SQLAlchemy()


class Project(db.Model):
    # primary & foreign keys
    id = Column(Integer, primary_key=True)

    # columns
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text, default="")
    date = Column(DateTime, server_default=db.func.now())
    settings_path = Column(db.Text, nullable=False)
    n_objects = Column(JSON)

    # relationships
    images = db.relationship('Image', backref='project', lazy=True)
    annotation_classes = db.relationship('AnnotationClass', backref='project', lazy=True)


class Image(db.Model):
    # primary & foreign keys
    id = Column(Integer, primary_key=True)
    proj_id = Column(Integer, ForeignKey('project.id'), nullable=False)

    # columns
    name = Column(Text, nullable=False)
    path = Column(Text)
    thumbnail_path = Column(Text)
    height = Column(Integer)
    width = Column(Integer)
    date = Column(DateTime, server_default=db.func.now())
    n_objects = Column(JSON)

    # relationships
    ground_truth_annotations = db.relationship('GroundTruthAnnotation', backref='image', lazy=True)
    predicted_annotations = db.relationship('PredictedAnnotation', backref='image', lazy=True)
    tiles = db.relationship('Tile', backref='image', lazy=True)


class AnnotationClass(db.Model):
    # primary & foreign keys
    id = Column(Integer, primary_key=True)
    proj_id = Column(Integer, ForeignKey('project.id'), nullable=False)

    # columns
    name = Column(Text, nullable=False, unique=True)
    color = Column(Text, nullable=False)
    magnification = Column(Integer, nullable=False)
    dl_model_path = Column(Text)


class GroundTruthAnnotation(db.Model):
    # primary & foreign keys
    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    annotation_class_id = Column(Integer, ForeignKey('annotation_class.id'), nullable=False)

    # columns
    centroid_x = Column(Integer)
    centroid_y = Column(Integer)
    area = Column(Integer)
    polygon = Column(Geometry('MULTIPOLYGON'))


class PredictedAnnotation(db.Model):
    # primary & foreign keys
    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    annotation_class_id = Column(Integer, ForeignKey('annotation_class.id'), nullable=False)

    # columns
    centroid_x = Column(Integer)
    centroid_y = Column(Integer)
    area = Column(Integer)
    polygon = Column(Geometry('MULTIPOLYGON'))


class Tile(db.Model):
    # primary & foreign keys
    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey(''))
    annotation_class_id = Column(Integer, ForeignKey('annotation_class.id'), nullable=False)

    # columns
    coord_x = Column(Integer, nullable=False)
    coord_y = Column(Integer, nullable=False)
    seen = Column(Integer, nullable=False, default=0)


class Notifications(db.Model):
    # primary & foreign keys
    id = Column(Integer, primary_key=True)

    # columns
    message_type = Column(Integer, nullable=False)
    read = Column(Boolean, nullable=False)






























































