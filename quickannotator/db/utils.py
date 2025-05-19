from quickannotator.db import Base, engine
from sqlalchemy import Table
import os
from datetime import datetime

from quickannotator.db.crud.image import get_image_by_id
from quickannotator.db.fsmanager import fsmanager

def create_dynamic_model(table_name, base=Base):
    class DynamicAnnotation(base):
        __tablename__ = table_name
        __table__ = Table(table_name, base.metadata, autoload_with=engine)

    return DynamicAnnotation


def build_annotation_table_name(image_id: int, annotation_class_id: int, is_gt: bool):
    gtpred = 'gt' if is_gt else 'pred'
    table_name = f"annotation_{image_id}_{annotation_class_id}_{gtpred}"
    return table_name

def build_tarpath(image_id: int, annotation_class_id: int, is_gt: bool):
    project_id = get_image_by_id(image_id).project_id
    save_path = fsmanager.nas_write.get_project_image_path(project_id, image_id)
    tarname = build_tarname(image_id, annotation_class_id, is_gt)
    tarpath = os.path.join(save_path, tarname)
    return tarpath

def build_tarname(image_id: int, annotation_class_id: int, is_gt: bool):
    """
    Build the tar name for a given image and annotation class.

    Args:
        image_id (int): The ID of the image.
        annotation_class_id (int): The ID of the annotation class.
        is_gt (bool): Flag indicating if the annotations are ground truth.

    Returns:
        str: The tar name for the specified image and annotation class.
    """
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    tarname = f'{table_name}.tar.gz'
    return tarname


