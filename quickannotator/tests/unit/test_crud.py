import pytest
from shapely.geometry import Polygon, shape
from quickannotator.api.v1.utils.shared_crud import AnnotationStore, upsert_tiles
from quickannotator.tests.conftest import assert_geojson_equal
from shapely.geometry import mapping
import geojson
from quickannotator.constants import TileStatus


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

    # Assert
    assert result


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

def test_upsert_gt_tiles(annotation_store):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    tile_ids = [1, 2, 3]

    # Act
    result = upsert_tiles(image_id, annotation_class_id, tile_ids)

    # Assert
    assert result is not None


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


def test_upsert_tiles_with_process_owns_tile(annotation_store):
    # Arrange
    image_id = 1
    annotation_class_id = 2
    tile_ids = [1, 2, 3]

    # Act
    result = upsert_tiles(image_id, annotation_class_id, tile_ids, process_owns_tile=True)

    # Assert
    assert result is not None


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
    assert result == 0
