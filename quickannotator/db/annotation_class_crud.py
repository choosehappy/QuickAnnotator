import quickannotator.db.models as models
from quickannotator.db import db_session


def get_annotation_class_by_id(annotation_class_id: int) -> models.AnnotationClass:
    return db_session.query(models.AnnotationClass).get(annotation_class_id)


def build_actor_name(annotation_class_id):
    return f"dl_actor_class_{annotation_class_id}"