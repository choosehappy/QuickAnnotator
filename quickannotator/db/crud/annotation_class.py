import quickannotator.db.models as db_models
from quickannotator.db import db_session


def get_annotation_class_by_id(annotation_class_id: int) -> db_models.AnnotationClass:
    return db_session.query(db_models.AnnotationClass).get(annotation_class_id)


def build_actor_name(annotation_class_id):
    return f"dl_actor_class_{annotation_class_id}"


def insert_annotation_class(project_id, name, color, work_mag, work_tilesize):
    annotation_class = db_models.AnnotationClass(project_id=project_id,
                                        name=name,
                                        color=color,
                                        work_mag=work_mag,
                                        work_tilesize=work_tilesize)
    db_session.add(annotation_class)