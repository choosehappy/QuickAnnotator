import geojson
from conftest import assert_geojson_equal
from quickannotator.db.crud.annotation import AnnotationStore
import quickannotator.db.models as db_models

def test_annotations_within_polygon(test_client, annotations_seed):
    """
    GIVEN a test client and annotations within a specific polygon
    WHEN the client requests the annotations within the polygon using a GET request
    THEN the response should have a status code of 200 and the returned data should match the annotations within the polygon
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    polygon = geojson.Polygon([[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]])

    # Act
    params = {
        'is_gt': True,  # Assuming ground truth annotations
        'polygon': geojson.dumps(polygon)
    }
    response = test_client.post(f'/api/v1/annotation/{image_id}/{annotation_class_id}/withinpoly', json=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    for annotation in data:
        assert 'id' in annotation
        assert 'tile_id' in annotation
        assert 'centroid' in annotation
        assert 'polygon' in annotation
        assert 'area' in annotation
        assert 'custom_metrics' in annotation
        assert 'datetime' in annotation

    # TODO: check equality between the returned annotations and the expected annotations


def test_post_annotation(test_client, db_session, tissue_mask_seed, annotations_seed):
    """
    GIVEN a test client and a new annotation
    WHEN the client posts the annotation using a POST request
    THEN the response should have a status code of 200 if the annotation intersects the mask
    OR a status code of 400 if the annotation does not intersect the mask
    """

    # Arrange
    annotation_class_id = 2  # Fake Class
    image_id = 1
    geojson_polygon = geojson.Polygon([[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]])
    params = {
        'polygons': [geojson.dumps(geojson_polygon)]
    }

    # Case 1: Annotation intersects the mask
    response = test_client.post(f'/api/v1/annotation/{image_id}/{annotation_class_id}', json=params)

    # Assert for success
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    annotation = data[0]
    assert 'id' in annotation
    assert 'tile_id' in annotation
    assert 'centroid' in annotation
    assert 'polygon' in annotation
    assert 'area' in annotation
    assert 'custom_metrics' in annotation
    assert 'datetime' in annotation
    assert_geojson_equal(geojson.loads(annotation['polygon']), geojson_polygon)

    # Check that the corresponding tile has been updated in the database
    tile_id = annotation['tile_id']
    tile = db_session.query(db_models.Tile).filter_by(image_id=image_id, annotation_class_id=annotation_class_id, tile_id=tile_id).first()
    assert tile is not None
    assert tile.gt_counter == 0

    # Case 2: Annotation does not intersect the mask
    # Remove the tissue mask to simulate no intersection
    mask_store = AnnotationStore(image_id, 1, is_gt=True, in_work_mag=False)
    mask_store.delete_all_annotations()
    db_session.commit()

    response = test_client.post(f'/api/v1/annotation/{image_id}/{annotation_class_id}', json=params)

    # Assert for failure
    assert response.status_code == 400
    data = response.get_json()


def test_put_annotation(test_client, annotations_seed):
    """
    GIVEN a test client and an existing annotation
    WHEN the client updates the annotation using a PUT request
    THEN the response should have a status code of 201 and the returned data should match the updated annotation
    """

    image_id = 1
    annotation_class_id = 2
    annotation_id = 1
    geojson_polygon = geojson.Polygon([[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]])
    params = {
        'is_gt': True,
        'polygon': geojson.dumps(geojson_polygon),
        'annotation_id': annotation_id
    }

    response = test_client.put(f'/api/v1/annotation/{image_id}/{annotation_class_id}', json=params)

    # Assert
    assert response.status_code == 201
    data = response.get_json()
    assert data['id'] == annotation_id
    assert_geojson_equal(geojson.loads(data['polygon']), geojson_polygon)
    assert data['area'] == 6.25
    assert data['custom_metrics'] == {'iou': 0.5}
    assert 'datetime' in data

