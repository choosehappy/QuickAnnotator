import quickannotator.db as qadb
from quickannotator.db import AnnotationClass
from sqlalchemy import func, Table
from sqlalchemy.orm import Session

def get_annotation_class_by_id(annotation_class_id: int) -> AnnotationClass:
    return qadb.db.session.query(AnnotationClass).get(annotation_class_id)

