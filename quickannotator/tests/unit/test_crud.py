import pytest
from shapely.geometry import Polygon, shape
from quickannotator.db.crud.annotation import AnnotationStore, table_exists
from quickannotator.db.crud.tile import TileStoreFactory, TileStore
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


def test_table_exists_with_existing_table(db_session, annotations_seed):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    is_gt = True
    table_name = f"annotation_{image_id}_{annotation_class_id}_gt"

    # Act
    result = table_exists(table_name)

    # Assert
    assert result is True


def test_table_exists_with_nonexistent_table(db_session, annotations_seed):
    # Arrange
    table_name = "nonexistent_table"

    # Act
    result = table_exists(table_name)

    # Assert
    assert result is False


def test_annotation_store_initialization_with_existing_table(db_session, annotations_seed):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    is_gt = True

    # Act
    store = AnnotationStore(image_id, annotation_class_id, is_gt)

    # Assert
    assert store is not None
    assert store.image_id == image_id
    assert store.annotation_class_id == annotation_class_id
    assert store.is_gt == is_gt


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

def test_delete_annotations(annotation_store):
    # Arrange
    polygons = [Polygon([(i, i), (i + 1, i), (i + 1, i + 1), (i, i + 1), (i, i)]) for i in range(3)]
    inserted_annotations = annotation_store.insert_annotations(polygons)
    annotation_ids = [annotation.id for annotation in inserted_annotations]

    # Act
    deleted_ids = annotation_store.delete_annotations(annotation_ids)

    # Assert
    assert len(deleted_ids) == len(annotation_ids)
    assert set(deleted_ids) == set(annotation_ids)

    # Verify that the annotations are no longer retrievable
    for annotation_id in annotation_ids:
        assert annotation_store.get_annotation_by_id(annotation_id) is None

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
    store = AnnotationStore(1, 2, True)
    
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


def test_drop_table(annotation_store):
    # Arrange
    annotation_id = 1

    # Act
    result = annotation_store.drop_table()

    # Assert
    assert result is None

    # Verify that the table no longer exists
    with pytest.raises(Exception):
        annotation_store.get_annotation_by_id(annotation_id)


# UPSERT TILES TESTS
@pytest.fixture(scope="function")
def insert_unseen_tile(db_session):
    tile_id = 9990
    image_id = 1
    annotation_class_id = 2

    tile = models.Tile(
        image_id=image_id,
        annotation_class_id=annotation_class_id,
        tile_id=tile_id,
        pred_status=TileStatus.UNSEEN
    )
    db_session.add(tile)
    db_session.commit()

    return tile


@pytest.fixture(scope="function")
def insert_startprocessing_tile(db_session):
    tile_id = 9991
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
    tile_id = 9992
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
    tile_id = 9993
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
    tile_id = 9994
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


def test_insert_gt_tiles_with_empty_list(db_session):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    tile_ids = []
    tilestore: TileStore = TileStoreFactory.get_tilestore()

    # Act
    result = tilestore.upsert_gt_tiles(image_id, annotation_class_id, tile_ids)

    # Assert
    assert result is not None
    assert len(result) == 0


def test_insert_gt_tiles_with_non_empty_list(db_session):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    tile_ids = [1, 2, 3]
    tilestore: TileStore = TileStoreFactory.get_tilestore()

    # Act
    result = tilestore.upsert_gt_tiles(image_id, annotation_class_id, tile_ids)

    # Assert
    assert result is not None
    assert len(result) == len(tile_ids)


def test_upsert_gt_tiles(insert_unseen_tile):
    # Arrange
    tile = insert_unseen_tile
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    assert tile.pred_status == TileStatus.UNSEEN
    assert tile.gt_counter is None
    assert tile.gt_datetime is None

    # Act
    result = tilestore.upsert_gt_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id])
    new_tile = result[0]

    # Assert
    assert new_tile.gt_counter == 0
    assert new_tile.gt_datetime is not None


def test_insert_pred_tiles_with_pred_status(annotation_store):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    tile_ids = [1, 2, 3]
    pred_status = TileStatus.DONEPROCESSING
    tilestore: TileStore = TileStoreFactory.get_tilestore()

    # Act
    result = tilestore.upsert_pred_tiles(image_id, annotation_class_id, tile_ids, pred_status=pred_status)

    # Assert
    assert result is not None
    assert len(result) == len(tile_ids)
    for tile in result:
        assert tile.pred_status == pred_status


def test_tile_UNSEEN_to_STARTPROCESSING(insert_unseen_tile: models.Tile):
    # Arrange
    tile = insert_unseen_tile
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    assert tile.pred_status == TileStatus.UNSEEN
    assert tile.pred_datetime is None

    initial_pred_datetime = tile.pred_datetime
    new_status = TileStatus.STARTPROCESSING
    process_owns_tile = False

    # Act
    result = tilestore.upsert_pred_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=new_status, process_owns_tile=process_owns_tile)

    # Assert
    assert len(result) == 1
    new_tile = result[0]
    assert new_tile.pred_status == new_status
    assert new_tile.pred_datetime != initial_pred_datetime


def test_tile_STARTPROCESSING_to_PROCESSING(insert_startprocessing_tile: models.Tile):
    # Arrange
    tile = insert_startprocessing_tile
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    assert tile.pred_status == TileStatus.STARTPROCESSING
    initial_pred_datetime = tile.pred_datetime
    new_status = TileStatus.PROCESSING
    process_owns_tile = False  # Should cause the upsert to fail

    # Act
    result = tilestore.upsert_pred_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=new_status, process_owns_tile=process_owns_tile)

    # Assert
    assert len(result) == 1
    new_tile = result[0]
    assert new_tile.pred_status == tile.pred_status
    assert new_tile.pred_datetime == initial_pred_datetime


def test_tile_PROCESSING_to_DONEPROCESSING(insert_processing_tile: models.Tile):
    # Arrange
    tile = insert_processing_tile
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    process_owns_tile = False  # Should cause the upsert to fail
    new_status = TileStatus.DONEPROCESSING
    assert tile.pred_status == TileStatus.PROCESSING
    initial_pred_datetime = tile.pred_datetime

    # Act
    result = tilestore.upsert_pred_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=new_status, process_owns_tile=process_owns_tile)

    # Assert
    assert len(result) == 1
    new_tile = result[0]
    assert new_tile.pred_status == tile.pred_status
    assert new_tile.pred_datetime == initial_pred_datetime


def test_tile_PROCESSING_to_DONEPROCESSING_with_process_owns_tile(insert_processing_tile: models.Tile):
    # Arrange
    tile = insert_processing_tile
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    process_owns_tile = True
    new_status = TileStatus.DONEPROCESSING
    assert tile.pred_status == TileStatus.PROCESSING
    initial_pred_datetime = tile.pred_datetime

    # Act
    result = tilestore.upsert_pred_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=new_status, process_owns_tile=process_owns_tile)

    # Assert
    assert len(result) == 1
    new_tile = result[0]
    assert new_tile.pred_status == new_status
    assert new_tile.pred_datetime != initial_pred_datetime


def test_DONEPROCESSING_to_STARTPROCESSING(insert_doneprocessing_tile: models.Tile):
    # Arrange
    tile = insert_doneprocessing_tile
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    new_status = TileStatus.STARTPROCESSING
    assert tile.pred_status == TileStatus.DONEPROCESSING
    initial_pred_datetime = tile.pred_datetime

    # Act
    result = tilestore.upsert_pred_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=new_status)

    # Assert
    assert len(result) == 1
    new_tile = result[0]
    assert new_tile.pred_status == tile.pred_status  # Should not change
    assert new_tile.pred_datetime == initial_pred_datetime  # Should not change


def test_stale_DONEPROCESSING_to_STARTPROCESSING(insert_stale_doneprocessing_tile: models.Tile):
    # Arrange
    tile = insert_stale_doneprocessing_tile
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    new_status = TileStatus.STARTPROCESSING
    assert tile.pred_status == TileStatus.DONEPROCESSING
    initial_pred_datetime = tile.pred_datetime

    # Act
    result = tilestore.upsert_pred_tiles(tile.image_id, tile.annotation_class_id, [tile.tile_id], pred_status=new_status)

    # Assert
    assert len(result) == 1
    new_tile = result[0]
    assert new_tile.pred_status == new_status  # Should change
    assert new_tile.pred_datetime != initial_pred_datetime  # Should change


def test_reset_all_PROCESSING_tiles_with_other_states(insert_processing_tile, insert_unseen_tile, insert_startprocessing_tile, insert_doneprocessing_tile, db_session):
    # Arrange
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    processing_tile = insert_processing_tile
    unseen_tile = insert_unseen_tile
    startprocessing_tile = insert_startprocessing_tile
    doneprocessing_tile = insert_doneprocessing_tile

    assert processing_tile.pred_status == TileStatus.PROCESSING
    assert unseen_tile.pred_status == TileStatus.UNSEEN
    assert startprocessing_tile.pred_status == TileStatus.STARTPROCESSING
    assert doneprocessing_tile.pred_status == TileStatus.DONEPROCESSING

    # Act
    tilestore.reset_all_PROCESSING_tiles(processing_tile.annotation_class_id)
    db_session.refresh(processing_tile)
    db_session.refresh(unseen_tile)
    db_session.refresh(startprocessing_tile)
    db_session.refresh(doneprocessing_tile)

    # Assert
    # Verify that only the PROCESSING tile was reset
    assert processing_tile.pred_status == TileStatus.UNSEEN
    assert processing_tile.pred_datetime is None

    # Verify that other tiles remain unchanged
    assert unseen_tile.pred_status == TileStatus.UNSEEN
    assert startprocessing_tile.pred_status == TileStatus.STARTPROCESSING
    assert doneprocessing_tile.pred_status == TileStatus.DONEPROCESSING
