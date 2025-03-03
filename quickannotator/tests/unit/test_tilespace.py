import pytest
from quickannotator.api.v1.utils.coordinate_space import TileSpace

def test_get_tile_ids_within_bbox(tilespace):
    bbox = [100, 100, 500, 500]
    expected_tile_ids = [5, 6, 7, 9, 10, 11, 13, 14, 15]
    assert tilespace.get_tile_ids_within_bbox(bbox) == expected_tile_ids

def test_point_to_tileid(tilespace):
    x, y = 300, 300
    expected_tile_id = 5
    assert tilespace.point_to_tileid(x, y) == expected_tile_id

def test_tileid_to_point(tilespace):
    tile_id = 5
    expected_point = (256, 256)
    assert tilespace.tileid_to_point(tile_id) == expected_point

def test_rc_to_tileid(tilespace):
    row, col = 1, 2
    expected_tile_id = 6
    assert tilespace.rc_to_tileid(row, col) == expected_tile_id

def test_tileid_to_rc(tilespace):
    tile_id = 6
    expected_rc = (1, 2)
    assert tilespace.tileid_to_rc(tile_id) == expected_rc

def test_get_all_tile_ids_for_image(tilespace):
    expected_tile_ids = list(range(16))
    assert tilespace.get_all_tile_ids_for_image() == expected_tile_ids

def test_get_bbox_for_tile(tilespace):
    tile_id = 5
    expected_bbox = (256, 256, 512, 512)
    assert tilespace.get_bbox_for_tile(tile_id) == expected_bbox