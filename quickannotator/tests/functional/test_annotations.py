from flask import Flask
import os
import pytest
from quickannotator.api.v1.annotation import bp as annotation_bp
from quickannotator.api.v1.annotation.helper import get_annotations_within_poly
from quickannotator.db import models
from shapely.geometry import Polygon
import geojson

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
    response = test_client.get(f'/api/v1/annotation/{image_id}/{annotation_class_id}/withinpoly', query_string=params)

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