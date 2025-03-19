from quickannotator.db import db_session
import quickannotator.db.models as models
from sqlalchemy import func, Table
from datetime import datetime


def insert_annotation_class(project_id, name, color, work_mag, work_tilesize):
    annotation_class = models.AnnotationClass(project_id=project_id,
                                        name=name,
                                        color=color,
                                        work_mag=work_mag,
                                        work_tilesize=work_tilesize)
    db_session.add(annotation_class)
