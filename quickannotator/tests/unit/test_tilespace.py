import pytest

def test_get_tile_ids_within_bbox(fake_ann_class_tilespace):
    bbox = [100, 100, 500, 500]
    expected_tile_ids = [0]
    assert fake_ann_class_tilespace.get_tile_ids_within_bbox(bbox) == expected_tile_ids

def test_point_to_tileid(fake_ann_class_tilespace):
    x, y = 300, 300
    expected_tile_id = 0
    assert fake_ann_class_tilespace.point_to_tileid(x, y) == expected_tile_id

def test_tileid_to_point(fake_ann_class_tilespace):
    tile_id = 0
    expected_point = (0, 0)
    assert fake_ann_class_tilespace.tileid_to_point(tile_id) == expected_point

def test_rc_to_tileid(fake_ann_class_tilespace):
    row, col = 1, 2
    expected_tile_id = 2
    assert fake_ann_class_tilespace.rc_to_tileid(row, col) == expected_tile_id

def test_tileid_to_rc(fake_ann_class_tilespace):
    tile_id = 2
    expected_rc = (0, 2)
    assert fake_ann_class_tilespace.tileid_to_rc(tile_id) == expected_rc

def test_get_all_tile_ids_for_image(fake_ann_class_tilespace):
    expected_tile_ids = list(range(1))
    assert fake_ann_class_tilespace.get_all_tile_ids_for_image() == expected_tile_ids

def test_get_bbox_for_tile(fake_ann_class_tilespace):
    tile_id = 0
    expected_bbox = (0, 0, 2048, 2048)
    assert fake_ann_class_tilespace.get_bbox_for_tile(tile_id) == expected_bbox