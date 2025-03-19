from quickannotator.db import db_session
import quickannotator.db.models as models
import large_image
import os
from datetime import datetime

def add_image_by_path(project_id, full_path):
    path = full_path.split("quickannotator/")[1]
    slide = large_image.getTileSource(full_path)
    name = os.path.basename(full_path)

    image = models.Image(project_id=project_id,
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


def get_image_by_id(image_id: int) -> models.Image:
    return db_session.query(models.Image).get(image_id)