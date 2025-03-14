from quickannotator.db import db_session
import quickannotator.db.models as models
from sqlalchemy import func, Table
from datetime import datetime


def get_annotation_class_by_id(annotation_class_id: int) -> models.AnnotationClass:
    return db_session.query(models.AnnotationClass).get(annotation_class_id)

def insert_annotation_class(project_id, name, color, work_mag, work_tilesize, dl_model_objectref):
    annotation_class = models.AnnotationClass(project_id=project_id,
                                        name=name,
                                        color=color,
                                        work_mag=work_mag,
                                        work_tilesize=work_tilesize,
                                        dl_model_objectref=dl_model_objectref,
                                        datetime=datetime.now())
    db_session.add(annotation_class)