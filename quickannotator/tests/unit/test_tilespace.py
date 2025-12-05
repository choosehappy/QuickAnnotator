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
    row, col = 1, 1
    expected_tile_id = 20
    assert fake_ann_class_tilespace.rc_to_tileid(row, col) == expected_tile_id

def test_tileid_to_rc(fake_ann_class_tilespace):
    tile_id = 2
    expected_rc = (0, 2)
    assert fake_ann_class_tilespace.tileid_to_rc(tile_id) == expected_rc

def test_get_all_tile_ids_for_image(fake_ann_class_tilespace):
    expected_number_of_tiles = 171
    expected_tile_ids = list(range(expected_number_of_tiles))
    assert fake_ann_class_tilespace.get_all_tile_ids_for_image() == expected_tile_ids

def test_get_bbox_for_tile(fake_ann_class_tilespace):
    tile_id = 0
    expected_bbox = (0, 0, 2048, 2048)
    assert fake_ann_class_tilespace.get_bbox_for_tile(tile_id) == expected_bbox


def test_get_resampled_tilespace(fake_ann_class_tilespace):
    downsample_level = 1
    upsample_level = 1

    # Test downsampling
    downsampled_tilespace = fake_ann_class_tilespace.get_resampled_tilespace(downsample_level, upsample=False)
    assert downsampled_tilespace.ts == fake_ann_class_tilespace.ts * (2 ** downsample_level)
    assert downsampled_tilespace.w == fake_ann_class_tilespace.w
    assert downsampled_tilespace.h == fake_ann_class_tilespace.h

    # Test upsampling
    upsampled_tilespace = downsampled_tilespace.get_resampled_tilespace(upsample_level, upsample=True)
    assert upsampled_tilespace.ts == fake_ann_class_tilespace.ts
    assert upsampled_tilespace.w == fake_ann_class_tilespace.w
    assert upsampled_tilespace.h == fake_ann_class_tilespace.h

def test_upsample_fractional_tilesize(fake_ann_class_tilespace):
    upsample_level = 2  # Choose a level that would result in a fractional tilesize

    # Modify the tilesize to make it incompatible with the upsample level
    fake_ann_class_tilespace.ts = 3

    with pytest.raises(ValueError, match="Upsample level must result in an even factor of the tile size."):
        fake_ann_class_tilespace.get_resampled_tilespace(upsample_level, upsample=True)

def test_tilespace_properties(fake_ann_class_tilespace):
    tileids = fake_ann_class_tilespace.get_all_tile_ids_for_image()


def test_downsample_tile_id(fake_ann_class_tilespace):
    # Image has 19 tiles across and 6 tiles down at base level

    # Test case 1
    tile_id = 20
    downsample_level = 1
    expected_downsampled_tile_id = 0
    assert fake_ann_class_tilespace.downsample_tile_id(tile_id, downsample_level) == expected_downsampled_tile_id

    # Test case 2
    tile_id = 38
    downsample_level = 1
    expected_downsampled_tile_id = 10
    assert fake_ann_class_tilespace.downsample_tile_id(tile_id, downsample_level) == expected_downsampled_tile_id

    # Test case 3
    tile_id = 57
    downsample_level = 2
    expected_downsampled_tile_id = 0
    assert fake_ann_class_tilespace.downsample_tile_id(tile_id, downsample_level) == expected_downsampled_tile_id

    # Test case 4
    tile_id = 114
    downsample_level = 2
    expected_downsampled_tile_id = 5
    assert fake_ann_class_tilespace.downsample_tile_id(tile_id, downsample_level) == expected_downsampled_tile_id


def test_get_all_tile_coordinates_for_image(fake_ann_class_tilespace):
    expected_coordinates = fake_ann_class_tilespace.get_all_tile_coordinates_for_image()
    actual_coordinates = [
        fake_ann_class_tilespace.tileid_to_point(tile_id)
        for tile_id in fake_ann_class_tilespace.get_all_tile_ids_for_image()
    ]
    assert expected_coordinates == actual_coordinates

def test_get_all_tile_rc_for_image(fake_ann_class_tilespace):
    expected_rc_indices = fake_ann_class_tilespace.get_all_tile_rc_for_image()
    actual_rc_indices = [
        fake_ann_class_tilespace.tileid_to_rc(tile_id)
        for tile_id in fake_ann_class_tilespace.get_all_tile_ids_for_image()
    ]
    assert expected_rc_indices == actual_rc_indices

def test_upsample_tile_id(fake_ann_class_tilespace):
    # Test case 1
    tile_id = 0
    upsample_level = 1
    expected_tile_ids = [0, 1, 37, 38]
    assert fake_ann_class_tilespace.upsample_tile_id(tile_id, upsample_level) == expected_tile_ids