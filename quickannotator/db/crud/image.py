import quickannotator.db.models as db_models
from quickannotator.db import db_session
import sqlalchemy

import large_image

from typing import List
import os


def add_image_by_path(project_id, full_path):
    path = full_path.split("quickannotator/")[1]
    slide = large_image.getTileSource(full_path)
    name = os.path.basename(full_path)

    image = db_models.Image(project_id=project_id,
                    name=name,
                    path=path,
                    base_height=slide.sizeY,
                    base_width=slide.sizeX,
                    dz_tilesize=slide.tileWidth,
                    embedding_coord="POINT (1 1)",
                    group_id=0,
                    split=0
                    )

    db_session.add(image)

def get_image_ids_by_project_id(project_id: int) -> List[int]:
    stmt = sqlalchemy.select(db_models.Image.id).where(db_models.Image.project_id==project_id)
    return db_session.execute(stmt).scalars().all()

def get_image_by_id(image_id: int) -> db_models.Image:
    return db_session.query(db_models.Image).get(image_id)