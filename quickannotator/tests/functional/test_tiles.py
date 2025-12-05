from flask import Flask
from quickannotator.constants import TileStatus
import geojson
import pytest
import quickannotator.db.models as db_models
from datetime import datetime, timedelta
import quickannotator.constants as constants

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

    # Act
    params = {
        'tile_id': tile_id
    }
    response = test_client.get(f'/api/v1/tile/{image_id}/{annotation_class_id}', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['annotation_class_id'] == annotation_class_id
    assert data['image_id'] == image_id
    assert data['tile_id'] == tile_id


def test_get_tile_bbox(test_client, seed, tissue_mask_seed, db_session):
    """
    GIVEN a test client and a tile with specific annotation_class_id, image_id, and tile_id
    WHEN the client requests the bounding box of the tile using a GET request
    THEN the response should have a status code of 200 and the returned data should match the bounding box of the requested tile
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    tile_id = 0

    # Act
    params = {
        'tile_id': tile_id
    }
    response = test_client.get(f'/api/v1/tile/{image_id}/{annotation_class_id}/bbox', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert 'bbox' in data


def test_search_tiles_within_bbox(test_client, seed, annotations_seed, db_session):
    """
    GIVEN a test client and tiles within a specific bounding box
    WHEN the client requests the tiles within the bounding box using a GET request
    THEN the response should have a status code of 200 and the returned data should match the tiles within the bounding box
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    bbox = {'x1': 0, 'y1': 0, 'x2': 100, 'y2': 100}
    hasgt = True

    # Act
    params = {
        'x1': bbox['x1'],
        'y1': bbox['y1'],
        'x2': bbox['x2'],
        'y2': bbox['y2'],
        'hasgt': hasgt
    }
    response = test_client.get(f'/api/v1/tile/{image_id}/{annotation_class_id}/search/bbox', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all('tile_id' in tile for tile in data)
    assert all('downsampled_tile_id' in tile for tile in data)

def test_get_tile_bbox(test_client, seed, tissue_mask_seed, db_session):
    """
    GIVEN a test client and a tile with specific annotation_class_id, image_id, and tile_id
    WHEN the client requests the bounding box of the tile using a GET request
    THEN the response should have a status code of 200 and the returned data should match the bounding box of the requested tile
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    tile_id = 0

    # Act
    params = {
        'tile_id': tile_id
    }
    response = test_client.get(f'/api/v1/tile/{image_id}/{annotation_class_id}/bbox', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert 'bbox_polygon' in data
    assert isinstance(data['bbox_polygon'], dict)
    assert data['bbox_polygon']['type'] == 'Polygon'
    assert len(data['bbox_polygon']['coordinates'][0]) == 5
    assert data['bbox_polygon']['coordinates'][0][0] == [0, 0]
    assert data['bbox_polygon']['coordinates'][0][1] == [8192, 0]
    assert data['bbox_polygon']['coordinates'][0][2] == [8192, 8192]
    assert data['bbox_polygon']['coordinates'][0][3] == [0, 8192]
    assert data['bbox_polygon']['coordinates'][0][4] == [0, 0]

def test_search_tile_by_polygon(test_client, seed, annotations_seed, db_session):
    """
    GIVEN a test client and tiles within a specific polygon
    WHEN the client requests the tiles within the polygon using a POST request
    THEN the response should have a status code of 200 and the returned data should match the tiles within the polygon
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    query_polygon = geojson.Polygon([[(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)]])
    hasgt = True

    # Act
    params = {
        'polygon': geojson.dumps(query_polygon),
        'hasgt': hasgt
    }
    response = test_client.post(f'/api/v1/tile/{image_id}/{annotation_class_id}/search/polygon', json=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all('tile_id' in tile for tile in data)
    assert all('downsampled_tile_id' in tile for tile in data)


def test_delete_tile(test_client, seed, db_session):
    """
    GIVEN a test client and a tile with specific annotation_class_id, image_id, and tile_id
    WHEN the client deletes the tile using a DELETE request
    THEN the response should have a status code of 204 and the tile should no longer exist in the database
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    tile_id = 0

    # Act
    params = {
        'tile_id': tile_id
    }
    response = test_client.delete(f'/api/v1/tile/{image_id}/{annotation_class_id}', query_string=params)

    # Assert
    assert response.status_code == 204


def test_tile_search_by_coordinates(test_client, seed, annotations_seed, db_session):
    """
    GIVEN a test client and a tile with specific coordinates
    WHEN the client requests the tile using the coordinates with a GET request
    THEN the response should have a status code of 200 and the returned data should match the requested tile's details
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    x, y = 9000, 0

    # Act
    params = {
        'x': x,
        'y': y
    }
    response = test_client.get(f'/api/v1/tile/{image_id}/{annotation_class_id}/search/coordinates', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert 'tile_id' in data
    assert isinstance(data['tile_id'], int)
    assert data['tile_id'] == 1

    
def test_predict_tile(test_client, seed, db_session):
    """
    GIVEN a test client and a tile with specific annotation_class_id, image_id, and tile_id
    WHEN the client stages the tile for DL processing using a POST request
    THEN the response should have a status code of 200 and the returned data should match the staged tile's details
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    tile_id = 0

    # Act
    params = {
        'tile_id': tile_id
    }
    response = test_client.post(f'/api/v1/tile/{image_id}/{annotation_class_id}/predict', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['annotation_class_id'] == annotation_class_id
    assert data['image_id'] == image_id
    assert data['tile_id'] == tile_id
    assert data['pred_status'] == TileStatus.STARTPROCESSING


def test_search_tiles_with_downsample_level(test_client, seed, annotations_seed, db_session):
    """
    GIVEN a test client and tiles within a specific bounding box
    WHEN the client requests the tiles within the bounding box using a GET request with a downsample_level
    THEN the response should have a status code of 200 and the returned data should include downsampled_tile_id values
    """

    # Arrange
    annotation_class_id = 2
    image_id = 1
    bbox = {'x1': 0, 'y1': 0, 'x2': 40000, 'y2': 40000}
    hasgt = False
    downsample_level = 1

    # Act
    params = {
        'x1': bbox['x1'],
        'y1': bbox['y1'],
        'x2': bbox['x2'],
        'y2': bbox['y2'],
        'hasgt': hasgt,
        'downsample_level': downsample_level
    }
    response = test_client.get(f'/api/v1/tile/{image_id}/{annotation_class_id}/search/bbox', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert all('tile_id' in tile for tile in data)
    assert all('downsampled_tile_id' in tile for tile in data)
    assert [tile['downsampled_tile_id'] for tile in data] == [0, 0, 1, 10, 10, 0, 1]
    assert [tile['tile_id'] for tile in data] == [0, 1, 2, 38, 39, 20, 21]
