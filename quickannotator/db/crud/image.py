import quickannotator.db.models as db_models
from quickannotator.db import db_session
from quickannotator.db.fsmanager import fsmanager
from sqlalchemy import func

import large_image

from typing import List
import os

def get_image_query():
    """Return a SQLAlchemy query for the Image model."""
    model = db_models.Image
    query = db_session.query(
        model.id,
        model.project_id,
        model.name,
        model.path,
        model.base_height,
        model.base_width,
        model.base_mag,
        model.dz_tilesize,
        func.ST_AsGeoJSON(model.embedding_coord).label('embedding_coord'),
        model.group_id,
        model.split,
        model.comment,
        model.datetime
    )

    return query

def is_dicom_tilesource(ts) -> bool:
    """Check whether a large_image tilesource handle represents a DICOM image."""
    try:
        metadata = ts.getInternalMetadata() or {}
    except Exception:
        metadata = {}

    if not isinstance(metadata, dict):
        return False

    openslide_meta = metadata.get('openslide', {})
    if isinstance(openslide_meta, dict):
        if openslide_meta.get('openslide.vendor', '').lower() == 'dicom':
            return True

    return False


def _find_largest_dicom_file(dir_path: str):
    """Find the largest DICOM file in a directory.

    Returns the file path if the largest file is a valid DICOM tilesource,
    otherwise returns None.
    """
    if not os.path.isdir(dir_path):
        return None
    saved_files = []
    for fname in os.listdir(dir_path):
        fpath = os.path.join(dir_path, fname)
        if os.path.isfile(fpath):
            saved_files.append((fname, fpath))
    if not saved_files:
        return None
    largest_file = max(saved_files, key=lambda x: os.path.getsize(x[1]))
    largest_filepath = largest_file[1]
    slide = large_image.getTileSource(largest_filepath)
    if is_dicom_tilesource(slide):
        return largest_filepath
    return None


def add_image_by_path(project_id, relative_path, name=None):
    """
    Add an image to the database using its path.
    Args:
        project_id (int): The ID of the project to which the image belongs.
        path (str): The file path of the image. Assumed to be within mounts_path.
        name (str, optional): The name of the image. If not provided, the name will be derived from the path.
    
    """
    fullpath = fsmanager.nas_read.relative_to_global(relative_path)
    slide = large_image.getTileSource(fullpath)
    
    if name is None:
        name = os.path.basename(fullpath)
    
    base_mag = float(slide.getMetadata()['magnification'])


    image = db_models.Image(project_id=project_id,
                    name=name,
                    path=relative_path,
                    base_height=slide.sizeY,
                    base_width=slide.sizeX,
                    base_mag=base_mag,
                    dz_tilesize=slide.tileWidth,
                    embedding_coord="POINT (1 1)",
                    group_id=0,
                    split=0
                    )

    db_session.add(image)
    db_session.commit()
    return image

def get_image_by_name(project_id: int, name: str) -> db_models.Image:
    return db_session.query(db_models.Image).filter(db_models.Image.project_id == project_id, db_models.Image.name == name).first()

def get_image_by_name_case_insensitive(project_id: int, name: str) -> db_models.Image:
    return db_session.query(db_models.Image).filter(db_models.Image.project_id == project_id, func.lower(db_models.Image.name) == name.lower()).first()

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