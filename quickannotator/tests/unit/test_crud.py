import pytest
from shapely.geometry import Polygon, shape
from quickannotator.api.v1.utils.shared_crud import AnnotationStore, upsert_tiles
from quickannotator.tests.conftest import assert_geojson_equal
from shapely.geometry import mapping
import geojson
from quickannotator.constants import TileStatus, TILE_PRED_EXPIRE
from quickannotator.db import models
from datetime import datetime, timedelta


@pytest.fixture
def annotation_store(db_session, seed, annotations_seed):
    image_id = 1
    annotation_class_id = 2
    is_gt = True
    return AnnotationStore(image_id, annotation_class_id, is_gt)


def test_insert_annotations(annotation_store):
    # Arrange
    polygons = [Polygon([(i, i), (i + 1, i), (i + 1, i + 1), (i, i + 1), (i, i)]) for i in range(5)]

    # Act
    result = annotation_store.insert_annotations(polygons)

    # Assert
    assert len(result) == 5


def test_get_annotation_by_id(annotation_store):
    # Arrange
    annotation_id = 1

    # Act
    annotation = annotation_store.get_annotation_by_id(annotation_id)

    # Assert
    assert annotation is not None
    assert annotation.id == annotation_id


def test_get_annotations_for_tiles(annotation_store):
    # Arrange
    tile_ids = [0]

    # Act
    annotations = annotation_store.get_annotations_for_tiles(tile_ids)

    # Assert
    assert len(annotations) > 0


def test_get_annotations_within_poly(annotation_store):
    # Arrange
    polygon = Polygon([(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0), (0.0, 0.0)])
    expected_polygons = [
        Polygon([[0, 0], [1250, 0], [1250, 1250], [0, 1250], [0, 0]])
    ]

    # Act
    annotations = annotation_store.get_annotations_within_poly(polygon)

    # Assert
    assert len(annotations) == len(expected_polygons)
    for annotation, expected_polygon in zip(annotations, expected_polygons):
        assert_geojson_equal(geojson.loads(annotation.polygon), geojson.loads(geojson.dumps(mapping(expected_polygon))))


def test_update_annotation(annotation_store):
    # Arrange
    annotation_id = 1
    geojson_polygon = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]]
    }
    new_polygon = shape(geojson_polygon)

    # Act
    result = annotation_store.update_annotation(annotation_id, new_polygon)

    # Assert
    assert_geojson_equal(geojson.loads(result.polygon), geojson_polygon)


def test_delete_annotation(annotation_store):
    # Arrange
    annotation_id = 1

    # Act
    result = annotation_store.delete_annotation(annotation_id)
    assert result == annotation_id


def test_delete_all_annotations(annotation_store):
    # Arrange
    tile_ids = [0]

    # Act
    annotation_store.delete_all_annotations()
    annotations = annotation_store.get_annotations_for_tiles(tile_ids)

    # Assert
    assert len(annotations) == 0


def test_create_annotation_table(seed):
    # Arrange
    polygons = [Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])]

    # Act
    store = AnnotationStore(1, 2, True, create_table=True)
    
    # Assert 
    result = store.insert_annotations(polygons)

    # Assert
    assert len(result) == 1
    assert_geojson_equal(geojson.loads(result[0].polygon), geojson.loads(geojson.dumps(mapping(polygons[0]))))


def test_insert_annotations_with_empty_list(annotation_store):
    # Arrange
    polygons = []

    # Act
    result = annotation_store.insert_annotations(polygons)

    # Assert
    assert len(result) == 0


def test_get_annotation_by_id_not_found(annotation_store):
    # Arrange
    annotation_id = 9999  # Assuming this ID does not exist

    # Act
    annotation = annotation_store.get_annotation_by_id(annotation_id)

    # Assert
    assert annotation is None


def test_update_annotation_not_found(annotation_store):
    # Arrange
    annotation_id = 9999  # Assuming this ID does not exist
    geojson_polygon = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]]
    }
    new_polygon = shape(geojson_polygon)

    # Act
    result = annotation_store.update_annotation(annotation_id, new_polygon)

    # Assert
    assert result is None


def test_delete_annotation_not_found(annotation_store):
    # Arrange
    annotation_id = 9999  # Assuming this ID does not exist

    # Act
    result = annotation_store.delete_annotation(annotation_id)

    # Assert
    assert result is None


# UPSERT TILES TESTS
@pytest.fixture(scope="function")
def insert_unseen_tile(db_session):
    tile_id = 9999
    image_id = 1
    annotation_class_id = 2

    tile = models.Tile(
        image_id=image_id,
        annotation_class_id=annotation_class_id,
        tile_id=tile_id,
        pred_status=None
    )
    db_session.add(tile)
    db_session.commit()

    return tile

@pytest.fixture(scope="function")
def insert_startprocessing_tile(db_session):
    tile_id = 9999
    image_id = 1
    annotation_class_id = 2

    tile = models.Tile(
        image_id=image_id,
        annotation_class_id=annotation_class_id,
        tile_id=tile_id,
        pred_status=TileStatus.STARTPROCESSING
    )
    db_session.add(tile)
    db_session.commit()

    return tile

@pytest.fixture(scope="function")
def insert_processing_tile(db_session):
    tile_id = 9999
    image_id = 1
    annotation_class_id = 2

    tile = models.Tile(
        image_id=image_id,
        annotation_class_id=annotation_class_id,
        tile_id=tile_id,
        pred_status=TileStatus.PROCESSING
    )
    db_session.add(tile)
    db_session.commit()

    return tile

@pytest.fixture(scope="function")
def insert_doneprocessing_tile(db_session):
    tile_id = 9999
    image_id = 1
    annotation_class_id = 2

    tile = models.Tile(
        image_id=image_id,
        annotation_class_id=annotation_class_id,
        tile_id=tile_id,
        pred_status=TileStatus.DONEPROCESSING
    )
    db_session.add(tile)
    db_session.commit()

    return tile

@pytest.fixture(scope="function")
def insert_stale_doneprocessing_tile(db_session):
    tile_id = 9999
    image_id = 1
    annotation_class_id = 2

    tile = models.Tile(
        image_id=image_id,
        annotation_class_id=annotation_class_id,
        tile_id=tile_id,
        pred_status=TileStatus.DONEPROCESSING,
        pred_datetime=datetime.now() - timedelta(minutes=(TILE_PRED_EXPIRE + 1))
    )
    db_session.add(tile)
    db_session.commit()

    return tile

def test_upsert_tiles_with_empty_list(db_session):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    tile_ids = []

    # Act
    result = upsert_tiles(image_id, annotation_class_id, tile_ids)

    # Assert
    assert result is not None
    assert len(result) == 0

def test_upsert_tiles_with_non_empty_list(db_session):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    tile_ids = [1, 2, 3]

    # Act
    result = upsert_tiles(image_id, annotation_class_id, tile_ids)

    # Assert
    assert result is not None
    assert len(result) == len(tile_ids)

def test_upsert_gt_tiles(annotation_store):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    tile_ids = [1, 2, 3]

    # Act
    result = upsert_tiles(image_id, annotation_class_id, tile_ids)

    # Assert
    assert result is not None
    assert len(result) == len(tile_ids)


def test_upsert_tiles_with_pred_status(annotation_store):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    tile_ids = [1, 2, 3]
    pred_status = TileStatus.DONEPROCESSING

    # Act
    result = upsert_tiles(image_id, annotation_class_id, tile_ids, pred_status=pred_status)

    # Assert
    assert result is not None
    assert len(result) == len(tile_ids)

def test_tile_UNSEEN_to_STARTPROCESSING(insert_unseen_tile: models.Tile):
    # Arrange
    tile = insert_unseen_tile
    assert tile.pred_status == TileStatus.UNSEEN

    # Act
    result = upsert_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=TileStatus.STARTPROCESSING)
    new_tile = result[0]

    # Assert
    assert new_tile.pred_status == TileStatus.STARTPROCESSING
    assert new_tile.pred_datetime != tile.pred_datetime

def test_tile_STARTPROCESSING_to_PROCESSING(insert_startprocessing_tile: models.Tile):
    # Arrange
    tile = insert_startprocessing_tile
    process_owns_tile = False # Should cause the upsert to fail
    assert tile.pred_status == TileStatus.STARTPROCESSING

    # Act
    result = upsert_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=TileStatus.PROCESSING, process_owns_tile=process_owns_tile)

    # Assert
    assert len(result) == 0

def test_tile_PROCESSING_to_DONEPROCESSING(insert_processing_tile: models.Tile):
    # Arrange
    tile = insert_processing_tile
    process_owns_tile = False # Should cause the upsert to fail
    assert tile.pred_status == TileStatus.PROCESSING

    # Act
    result = upsert_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=TileStatus.DONEPROCESSING)
    assert len(result) == 0

def test_tile_PROCESSING_to_DONEPROCESSING_with_process_owns_tile(insert_processing_tile: models.Tile):
    # Arrange
    tile = insert_processing_tile
    process_owns_tile = True
    assert tile.pred_status == TileStatus.PROCESSING

    # Act
    result = upsert_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=TileStatus.DONEPROCESSING, process_owns_tile=process_owns_tile)
    new_tile = result[0]

    # Assert
    assert new_tile.pred_status == TileStatus.DONEPROCESSING
    assert new_tile.pred_datetime != tile.pred_datetime


def test_DONEPROCESSING_to_STARTPROCESSING(insert_doneprocessing_tile: models.Tile):
    # Arrange
    tile = insert_doneprocessing_tile
    assert tile.pred_status == TileStatus.DONEPROCESSING

    # Act
    result = upsert_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=TileStatus.STARTPROCESSING)

    # Assert
    assert len(result) == 0     # Should fail because the tile is still fresh

def test_stale_DONEPROCESSING_to_STARTPROCESSING(insert_stale_doneprocessing_tile: models.Tile):
    # Arrange
    tile = insert_stale_doneprocessing_tile
    assert tile.pred_status == TileStatus.DONEPROCESSING

    # Act
    result = upsert_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=TileStatus.STARTPROCESSING)
    new_tile = result[0]
    # Assert
    assert new_tile.pred_status == TileStatus.STARTPROCESSING   # Should change
    assert new_tile.pred_datetime != tile.pred_datetime     # Should change