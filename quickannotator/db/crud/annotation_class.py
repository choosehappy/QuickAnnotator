import quickannotator.db.models as db_models
from quickannotator.db import db_session
import sqlalchemy
from typing import List
import quickannotator.constants as constants

def get_annotation_class_by_id(annotation_class_id: int) -> db_models.AnnotationClass:
    return db_session.query(db_models.AnnotationClass).get(annotation_class_id)


def get_all_annotation_class() ->List[db_models.AnnotationClass]:
    return db_session.query(db_models.AnnotationClass).all()
    
def build_actor_name(annotation_class_id):
    return f"dl_actor_class_{annotation_class_id}"


def insert_annotation_class(project_id: int, name: str, color: str, work_mag: int, work_tilesize: int):
    annotation_class = db_models.AnnotationClass(project_id=project_id,
                                        name=name,
                                        color=color,
                                        work_mag=work_mag,
                                        work_tilesize=work_tilesize)
    db_session.add(annotation_class)
    db_session.commit()
    return annotation_class

def put_annotation_class(annotation_class_id, name: str=None, color: str=None):
    annotation_class = db_session.query(db_models.AnnotationClass).get(annotation_class_id)
    if annotation_class is None:
        return None

    if name is not None:
        annotation_class.name = name
    if color is not None:
        annotation_class.color = color

    db_session.commit()
    return annotation_class

def delete_annotation_class(annotation_class_id: int) -> db_models.AnnotationClass:
    annotation_class: db_models.AnnotationClass = db_session.query(db_models.AnnotationClass).get(annotation_class_id)
    if annotation_class is None:
        return None

    db_session.delete(annotation_class)
    db_session.commit()
    return annotation_class

def search_annotation_class_by_name(name: str):
    return db_session.query(db_models.AnnotationClass).filter(db_models.AnnotationClass.name == name).all()

def search_annotation_class_by_project_id(project_id: int):
    return db_session.query(db_models.AnnotationClass).filter(
        (db_models.AnnotationClass.project_id == project_id) | 
        (db_models.AnnotationClass.project_id == None)
    ).all()


def insert_tissue_mask_class():
    if not get_annotation_class_by_id(constants.MASK_CLASS_ID):
        insert_annotation_class(
            project_id=None, 
            name=constants.MASK_CLASS_NAME, 
            color=constants.ANNOTATION_CLASS_COLOR_PALETTES[constants.COLOR_PALETTE_NAME][constants.MASK_CLASS_COLOR_IDX], 
            work_mag=constants.MASK_CLASS_WORK_TILESIZE, 
            work_tilesize=constants.MASK_CLASS_WORK_MAG
        )