from flask import Flask
import os
import pytest
from quickannotator.api.v1.annotation import bp as annotation_bp
from quickannotator.api.v1.annotation.helper import get_annotations_within_poly
from quickannotator.db import models
from shapely.geometry import Polygon
import geojson
from conftest import assert_geojson_equal

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


def test_put_annotation(test_client, annotations_seed):
    """
    GIVEN a test client and an existing annotation
    WHEN the client updates the annotation using a PUT request
    THEN the response should have a status code of 201 and the returned data should match the updated annotation
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    annotation_id = 1  # Assuming this annotation exists
    updated_polygon = geojson.Polygon([[(1, 1), (9, 1), (9, 9), (1, 9), (1, 1)]])
    updated_centroid = geojson.Point((5, 5))
    updated_area = 64.0
    updated_custom_metrics = {"metric1": 0.9, "metric2": 0.8}

    # Act
    params = {
        'id': annotation_id,
        'is_gt': True,
        'tile_id': 1,
        'centroid': geojson.dumps(updated_centroid),
        'polygon': geojson.dumps(updated_polygon),
        'area': updated_area,
        'custom_metrics': updated_custom_metrics,
        'datetime': '2023-10-10T10:10:10'
    }
    response = test_client.put(f'/api/v1/annotation/{image_id}/{annotation_class_id}', json=params)

    # Assert
    assert response.status_code == 201
    data = response.get_json()
    assert data['id'] == annotation_id
    assert data['tile_id'] == 1
    assert_geojson_equal(geojson.loads(data['polygon']), updated_polygon)
    assert_geojson_equal(geojson.loads(data['centroid']), updated_centroid)
    assert data['area'] == updated_area
    assert data['custom_metrics'] == updated_custom_metrics
    assert 'datetime' in data
