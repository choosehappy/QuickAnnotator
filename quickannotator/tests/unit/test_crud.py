import pytest
from shapely.geometry import Polygon, shape
from quickannotator.api.v1.utils.shared_crud import AnnotationStore
from quickannotator.tests.conftest import assert_geojson_equal
from shapely.geometry import mapping
import geojson


@pytest.fixture
def annotation_store(db_session, seed, annotations_seed):
    image_id = 1
    annotation_class_id = 2
    is_gt = True
    return AnnotationStore(image_id, annotation_class_id, is_gt)

def test_insert_annotations(annotation_store):
    polygons = [Polygon([(i, i), (i + 1, i), (i + 1, i + 1), (i, i + 1), (i, i)]) for i in range(5)]
    result = annotation_store.insert_annotations(polygons)
    assert len(result) == 5

def test_get_annotation_by_id(annotation_store):
    annotation_id = 1
    annotation = annotation_store.get_annotation_by_id(annotation_id)
    assert annotation is not None
    assert annotation.id == annotation_id

def test_get_annotations_for_tiles(annotation_store):
    tile_ids = [0]
    annotations = annotation_store.get_annotations_for_tiles(tile_ids)
    assert len(annotations) > 0

def test_get_annotations_within_poly(annotation_store):
    polygon = Polygon([(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0), (0.0, 0.0)])
    annotations = annotation_store.get_annotations_within_poly(polygon)
    expected_polygons = [
        Polygon([[0, 0], [1250, 0], [1250, 1250], [0, 1250], [0, 0]])
    ]
    
    assert len(annotations) == len(expected_polygons)
    
    for annotation, expected_polygon in zip(annotations, expected_polygons):
        assert_geojson_equal(geojson.loads(annotation.polygon), geojson.loads(geojson.dumps(mapping(expected_polygon))))

def test_update_annotation(annotation_store):
    annotation_id = 1
    geojson_polygon = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]]            
    }
    new_polygon = shape(geojson_polygon)
    result = annotation_store.update_annotation(annotation_id, new_polygon)
    assert_geojson_equal(geojson.loads(result.polygon), geojson_polygon)

def test_delete_annotation(annotation_store):
    annotation_id = 1
    result = annotation_store.delete_annotation(annotation_id)
    assert result == annotation_id

def test_delete_all_annotations(annotation_store):
    annotation_store.delete_all_annotations()
    annotations = annotation_store.get_annotations_for_tiles([0])
    assert len(annotations) == 0

def test_create_annotation_table(annotation_store):
    AnnotationStore(1, 2, True, create_table=True)
    # Assuming the table creation does not raise any exceptions, the test passes