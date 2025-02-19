from flask import Flask
import os
import pytest
from quickannotator.api.v1.tile import bp as tile_bp
from quickannotator.api.v1.tile.helper import upsert_tile
from quickannotator.constants import TileStatus
from quickannotator.db import models


def test_get_tile(test_client, seed, db_session):
    """
    GIVEN a test client and a tile with specific annotation_class_id, image_id, and tile_id
    WHEN the client requests the tile using a GET request
    THEN the response should have a status code of 200 and the returned data should match the requested tile's details
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    tile_id = 0
    seen = TileStatus.UNSEEN

    # Act
    params = {
        'annotation_class_id': annotation_class_id,
        'image_id': image_id,
        'tile_id': tile_id
    }
    response = test_client.get('/api/v1/tile', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['annotation_class_id'] == annotation_class_id
    assert data['image_id'] == image_id
    assert data['tile_id'] == tile_id
    assert data['seen'] == seen

# TODO: need to add annotation_1_1_gt and a tissue mask annotation for this to work
def test_get_tile_bbox(test_client, seed, db_session):
    """
    GIVEN a test client and a tile with specific annotation_class_id, image_id, and tile_id
    WHEN the client requests the bounding box of the tile using a GET request
    THEN the response should have a status code of 200 and the returned data should match the bounding box of the requested tile
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    tile_id = 0
    seen = TileStatus.UNSEEN

    # Act
    params = {
        'annotation_class_id': annotation_class_id,
        'image_id': image_id,
        'tile_id': tile_id
    }
    response = test_client.get('/api/v1/tile/bbox', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert 'bbox' in data


def test_search_tiles_within_bbox(test_client, seed, db_session):
    """
    GIVEN a test client and tiles within a specific bounding box
    WHEN the client requests the tiles within the bounding box using a GET request
    THEN the response should have a status code of 200 and the returned data should match the tiles within the bounding box
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    tile_id = 0
    include_placeholder_tiles = 'true'
    seen = TileStatus.UNSEEN

    bbox = {'x1': 0, 'y1': 0, 'x2': 100, 'y2': 100}

    # Act
    params = {
        'annotation_class_id': annotation_class_id,
        'image_id': image_id,
        'x1': bbox['x1'],
        'y1': bbox['y1'],
        'x2': bbox['x2'],
        'y2': bbox['y2'],
        'include_placeholder_tiles': include_placeholder_tiles
    }
    response = test_client.get('/api/v1/tile/search/bbox', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_search_tile_by_coordinates(test_client, seed, db_session):
    """
    GIVEN a test client and a tile with specific coordinates
    WHEN the client requests the tile using the coordinates with a GET request
    THEN the response should have a status code of 200 and the returned data should match the requested tile's details
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    tile_id = 0
    seen = TileStatus.UNSEEN

    x, y = 50, 50

    # Act
    params = {
        'annotation_class_id': annotation_class_id,
        'image_id': image_id,
        'x': x,
        'y': y
    }
    response = test_client.get('/api/v1/tile/search/coordinates', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['annotation_class_id'] == annotation_class_id
    assert data['image_id'] == image_id
    assert data['tile_id'] == tile_id
    assert data['seen'] == seen


def test_predict_tile(test_client, seed, db_session):
    """
    GIVEN a test client and a tile with specific annotation_class_id, image_id, and tile_id
    WHEN the client requests to predict the tile using a POST request
    THEN the response should have a status code of 201 and the returned data should contain the object reference
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    tile_id = 0
    seen = TileStatus.UNSEEN

    # Act
    response = test_client.post('/api/v1/tile/predict', json={
        'annotation_class_id': annotation_class_id,
        'image_id': image_id,
        'tile_id': tile_id
    })

    # Assert
    assert response.status_code == 201
    data = response.get_json()
    assert 'object_ref' in data