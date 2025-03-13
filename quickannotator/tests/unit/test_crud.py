import geojson
from quickannotator.api.v1.utils.shared_crud import bulk_insert_annotations, get_annotation_query, insert_new_annotation, upsert_tiles
from quickannotator.db.utils import create_dynamic_model, build_annotation_table_name
from quickannotator.api.v1.tile.helper import base_to_work_scaling_factor
from shapely.geometry import shape, Polygon
from conftest import assert_geojson_equal
from quickannotator.api.v1.tile.helper import base_to_work_scaling_factor
from quickannotator.constants import TileStatus
from quickannotator.db import models

def test_insert_new_annotation(db_session, annotations_seed):
    """
    GIVEN a new annotation
    WHEN the annotation is inserted
    THEN the annotation should be present in the database
    """
    # Arrange
    annotation_class_id = 2
    image_id = 1
    polygon = geojson.Polygon([[(0, 0), (3, 0), (3, 3), (0, 3), (0, 0)]])
    shapely_polygon = shape(polygon)

    # Act
    model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, True))
    db_session.query(model).delete()
    ann = insert_new_annotation(image_id, annotation_class_id, True, 0, shapely_polygon)

    # Assert
    model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, True))
    result: models.Annotation = get_annotation_query(model).filter_by(id=ann.id).all()
    assert len(result) == 1
    assert_geojson_equal(geojson.loads(result[0].polygon), polygon)

def test_bulk_annotations_insert(db_session,annotations_seed):
    """
    GIVEN a set of annotations
    WHEN the annotations are bulk inserted
    THEN the number of annotations in the database should match the number of inserted annotations
    """
    # Arrange
    annotation_class_id = 2
    image_id = 1

    # These polygons are already in the work magnification
    polygons = [
        geojson.Polygon([[(0, 0), (5, 0), (5, 5), (0, 5), (0, 0)]]),
        geojson.Polygon([[(5, 5), (10, 5), (10, 10), (5, 10), (5, 5)]])
    ]
    shapely_polygons = [shape(polygon) for polygon in polygons]

    # Act
    model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, True))
    db_session.query(model).delete()
    bulk_insert_annotations(image_id, annotation_class_id, True, shapely_polygons, from_work_mag=True)

    # Assert
    model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, True))
    query = get_annotation_query(model) 
    result = query.all()
    assert len(result) == len(polygons)
    for annotation, polygon in zip(result, polygons):
        assert_geojson_equal(geojson.loads(annotation.polygon), polygon)


def test_bulk_upsert_tiles(db_session, seed):
    """
    GIVEN a set of tiles
    WHEN the tiles are bulk upserted
    THEN the number of tiles in the database should match the number of upserted tiles
    """
    # Arrange
    annotation_class_id = 2
    image_id = 1
    tile_ids = [1, 2, 3, 4, 5]
    seen_status = TileStatus.DONEPROCESSING
    hasgt = True

    # Act
    db_session.query(models.Tile).delete()
    upsert_tiles(annotation_class_id, image_id, tile_ids, seen=seen_status, hasgt=hasgt)

    # Assert
    result = db_session.query(models.Tile).filter_by(annotation_class_id=annotation_class_id, image_id=image_id).all()
    assert len(result) == len(tile_ids)
    for tile in result:
        assert tile.seen == seen_status
        assert tile.hasgt == hasgt
        assert tile.annotation_class_id == annotation_class_id
        assert tile.image_id == image_id
        assert tile.tile_id in tile_ids
