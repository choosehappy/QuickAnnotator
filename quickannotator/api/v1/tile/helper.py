import quickannotator.db as qadb
from sqlalchemy import func
from quickannotator.db import db

def tiles_within_bbox(db, image_id, annotation_class_id, x1, y1, x2, y2):
    envelope = func.BuildMbr(x1, y1, x2, y2)

    tiles = db.session.query(qadb.Tile).filter(
        qadb.Tile.image_id == image_id,
        qadb.Tile.annotation_class_id == annotation_class_id,
        qadb.Tile.geom.ST_Intersects(envelope)
    ).all()

    return tiles