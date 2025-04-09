import geojson
from conftest import assert_geojson_equal
import quickannotator.db.models as models

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


def test_post_annotation(test_client, annotations_seed, db_session):
    """
    GIVEN a test client and a new annotation
    WHEN the client posts the annotation using a POST request
    THEN the response should have a status code of 200 and the returned data should match the posted annotation
    AND the corresponding tile should be updated in the database
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    geojson_polygon = geojson.Polygon([[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]])
    params = {
        'polygons': [geojson.dumps(geojson_polygon)]
    }

    # Act
    response = test_client.post(f'/api/v1/annotation/{image_id}/{annotation_class_id}', json=params)

    # Assert
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
    tile = db_session.query(models.Tile).filter_by(image_id=image_id, annotation_class_id=annotation_class_id, tile_id=tile_id).first()
    assert tile is not None
    assert tile.gt_counter == 0

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

