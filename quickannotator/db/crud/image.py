import quickannotator.db.models as db_models
from quickannotator.db import db_session
from quickannotator.db.fsmanager import fsmanager
from sqlalchemy import func

import large_image

from typing import List
import os


def add_image_by_path(project_id, relative_path):
    """
    Add an image to the database using its path.
    Args:
        project_id (int): The ID of the project to which the image belongs.
        path (str): The file path of the image. Assumed to be within mounts_path.
    
    """
    fullpath = fsmanager.nas_read.relative_to_global(relative_path)
    slide = large_image.getTileSource(fullpath)
    name = os.path.basename(fullpath)

    image = db_models.Image(project_id=project_id,
                    name=name,
                    path=relative_path,
                    base_height=slide.sizeY,
                    base_width=slide.sizeX,
                    dz_tilesize=slide.tileWidth,
                    embedding_coord="POINT (1 1)",
                    group_id=0,
                    split=0
                    )

    db_session.add(image)
    db_session.commit()
    return image

def get_image_by_name(name: str) -> db_models.Image:
    return db_session.query(db_models.Image).filter(db_models.Image.name == name).first()

def get_image_by_name_case_insensitive(name: str) -> db_models.Image:
    return db_session.query(db_models.Image).filter(func.lower(db_models.Image.name) == name.lower()).first()

def get_images_by_project_id(project_id: int) -> List[db_models.Image]:
    return db_session.query(db_models.Image).filter(db_models.Image.project_id==project_id).all()

def get_image_by_id(image_id: int) -> db_models.Image:
    return db_session.query(db_models.Image).get(image_id)

def get_images_for_project(project_id: int) -> list[db_models.Image]:
    return db_session.query(db_models.Image).filter(db_models.Image.project_id == project_id).all()

def delete_images(image_ids: List[int] | int):
    """
    Delete images by their IDs.
    Args:
        image_ids (List[int] | int): A list of image IDs or a single image ID to delete.
    """
    if isinstance(image_ids, int):
        image_ids = [image_ids]
    
    db_session.query(db_models.Image).filter(db_models.Image.id.in_(image_ids)).delete(synchronize_session=False)
    db_session.commit()