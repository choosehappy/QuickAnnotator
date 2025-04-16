import quickannotator.db.models as db_models
from quickannotator.db import db_session


import large_image


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


def get_image_by_id(image_id: int) -> db_models.Image:
    return db_session.query(db_models.Image).get(image_id)