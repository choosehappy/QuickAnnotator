from datetime import datetime
from sqlalchemy.orm import aliased, sessionmaker, Session
import quickannotator.db as qadb
from quickannotator.db import build_annotation_table_name, create_dynamic_model
import shapely
import json

# TODO: Remove session from params
def get_tile(session: Session, annotation_class_id: int, image_id: int, tile_id: int) -> qadb.Tile:
    result = session.query(qadb.Tile).filter_by(
        annotation_class_id=annotation_class_id,
        image_id=image_id,
        tile_id=tile_id
    ).first()
    return result


def compute_custom_metrics() -> dict:
    return json.dumps({"iou": 0.5})

# TODO: Remove session from params
def insert_new_annotation(session, image_id, annotation_class_id, is_gt, polygon: shapely.geometry.Polygon):
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    model = create_dynamic_model(table_name)

    new_annotation = model(
        image_id=None,
        annotation_class_id=None,
        isgt=None,
        centroid=polygon.centroid.wkt,
        area=polygon.area,
        polygon=polygon.wkt,
        custom_metrics=compute_custom_metrics(),
        datetime=datetime.now()
    )
    session.add(new_annotation)
    session.commit()
    return new_annotation
