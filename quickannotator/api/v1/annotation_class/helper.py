import quickannotator.db as qadb
from sqlalchemy import func, Table
from sqlalchemy.orm import Session

def annotation_class_by_id(session: Session, annotation_class_id: int) -> qadb.AnnotationClass:
    return session.query(qadb.AnnotationClass).get(annotation_class_id)