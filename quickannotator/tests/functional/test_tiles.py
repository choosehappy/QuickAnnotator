from flask import Flask
from quickannotator.constants import TileStatus
from quickannotator.api.v1.utils.shared_crud import upsert_tiles
import geojson
import pytest
import quickannotator.db.models as models
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
    assert 'tile_ids' in data
    assert isinstance(data['tile_ids'], list)
    assert len(data['tile_ids']) > 0


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
    assert 'tile_ids' in data
    assert isinstance(data['tile_ids'], list)
    assert len(data['tile_ids']) > 0


def test_search_tile_by_coordinates(test_client, seed, annotations_seed, db_session):
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
    assert 'tile_ids' in data
    assert isinstance(data['tile_ids'], list)
    assert len(data['tile_ids']) == 1
    assert data['tile_ids'][0] == 1

    
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
