from flask import Flask
import os
import pytest
from quickannotator.api.v1.tile import bp as tile_bp
from quickannotator.api.v1.tile.helper import upsert_tile
from quickannotator.constants import TileStatus


def test_get_tile(test_client):
    """
    GIVEN a test client and a tile with specific annotation_class_id, image_id, and tile_id
    WHEN the client requests the tile using a GET request
    THEN the response should have a status code of 200 and the returned data should match the requested tile's details
    """

    # Arrange
    annotation_class_id = 1
    image_id = 1
    tile_id = 1
    seen = TileStatus.UNSEEN

    upsert_tile(annotation_class_id, image_id, tile_id, seen=seen)

    # Act
    response = test_client.get(f'/api/v1/tile?annotation_class_id={annotation_class_id}&image_id={image_id}&tile_id={tile_id}')

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['annotation_class_id'] == annotation_class_id
    assert data['image_id'] == image_id
    assert data['tile_id'] == tile_id
    assert data['seen'] == seen


def test_get_tile_bbox(test_client):
    """
    GIVEN a test client and a tile with specific annotation_class_id, image_id, and tile_id
    WHEN the client requests the bounding box of the tile using a GET request
    THEN the response should have a status code of 200 and the returned data should match the bounding box of the requested tile
    """

    # Arrange
    annotation_class_id = 1
    image_id = 1
    tile_id = 1
    upsert_tile(annotation_class_id, image_id, tile_id, seen=1)

    # Act
    response = test_client.get(f'/tile/bbox?annotation_class_id={annotation_class_id}&image_id={image_id}&tile_id={tile_id}')

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert 'bbox' in data


def test_search_tiles_within_bbox(test_client):
    """
    GIVEN a test client and tiles within a specific bounding box
    WHEN the client requests the tiles within the bounding box using a GET request
    THEN the response should have a status code of 200 and the returned data should match the tiles within the bounding box
    """

    # Arrange
    annotation_class_id = 1
    image_id = 1
    tile_id = 1
    upsert_tile(annotation_class_id, image_id, tile_id, seen=1)

    bbox = {'x1': 0, 'y1': 0, 'x2': 100, 'y2': 100}

    # Act
    response = test_client.get(f'/tile/search/bbox?annotation_class_id={annotation_class_id}&image_id={image_id}&x1={bbox["x1"]}&y1={bbox["y1"]}&x2={bbox["x2"]}&y2={bbox["y2"]}')

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_search_tile_by_coordinates(test_client):
    """
    GIVEN a test client and a tile with specific coordinates
    WHEN the client requests the tile using the coordinates with a GET request
    THEN the response should have a status code of 200 and the returned data should match the requested tile's details
    """

    # Arrange
    annotation_class_id = 1
    image_id = 1
    tile_id = 1
    upsert_tile(annotation_class_id, image_id, tile_id, seen=1)

    x, y = 50, 50

    # Act
    response = test_client.get(f'/tile/search/coordinates?annotation_class_id={annotation_class_id}&image_id={image_id}&x={x}&y={y}')

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['annotation_class_id'] == annotation_class_id
    assert data['image_id'] == image_id
    assert data['tile_id'] == tile_id
    assert data['seen'] == 1


def test_predict_tile(test_client):
    """
    GIVEN a test client and a tile with specific annotation_class_id, image_id, and tile_id
    WHEN the client requests to predict the tile using a POST request
    THEN the response should have a status code of 201 and the returned data should contain the object reference
    """

    # Arrange
    annotation_class_id = 1
    image_id = 1
    tile_id = 1
    upsert_tile(annotation_class_id, image_id, tile_id, seen=1)

    # Act
    response = test_client.post('/tile/predict', json={
        'annotation_class_id': annotation_class_id,
        'image_id': image_id,
        'tile_id': tile_id
    })

    # Assert
    assert response.status_code == 201
    data = response.get_json()
    assert 'object_ref' in data