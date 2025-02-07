from quickannotator.db import db_session
import quickannotator.db.models as models
from sqlalchemy import func, Table


def get_annotation_class_by_id(annotation_class_id: int) -> models.AnnotationClass:
    return db_session.query(models.AnnotationClass).get(annotation_class_id)

