import os
import pytest
from quickannotator.db.fsmanager import FileSystemManager

@pytest.fixture
def fs_manager():
    return FileSystemManager()

def test_nas_read_base_path(fs_manager):
    assert fs_manager.nas_read.get_base_path() == fs_manager.nas_read.base_path

def test_nas_read_full_path(fs_manager):
    expected_path = os.path.join(fs_manager.nas_read.base_path, "nas_read")
    assert fs_manager.nas_read.get_full_path() == expected_path

def test_nas_read_input_images_path(fs_manager):
    expected_path = os.path.join(fs_manager.nas_read.full_path, "images")
    assert fs_manager.nas_read.get_input_images_path() == expected_path

def test_nas_read_input_masks_dir(fs_manager):
    expected_path = os.path.join(fs_manager.nas_read.full_path, "masks")
    assert fs_manager.nas_read.get_input_masks_dir() == expected_path

def test_nas_write_project_image_path(fs_manager):
    proj_id = 1
    img_id = 2
    expected_path = os.path.join(
        fs_manager.nas_write.full_path, "projects", f"proj_{proj_id}", "images", f"img_{img_id}"
    )
    assert fs_manager.nas_write.get_project_image_path(proj_id, img_id) == expected_path

def test_nas_write_project_mask_path(fs_manager):
    proj_id = 1
    img_id = 2
    expected_path = os.path.join(
        fs_manager.nas_write.full_path, "projects", f"proj_{proj_id}", "images", f"img_{img_id}", "masks"
    )
    assert fs_manager.nas_write.get_project_mask_path(proj_id, img_id) == expected_path

def test_nas_write_class_checkpoint_path(fs_manager):
    annotation_class_id = 3
    expected_path = os.path.join(
        fs_manager.nas_write.full_path, "classes", f"class_{annotation_class_id}", "checkpoints"
    )
    assert fs_manager.nas_write.get_class_checkpoint_path(annotation_class_id) == expected_path

def test_nas_write_temp_image_path(fs_manager):
    expected_path = os.path.join(fs_manager.nas_write.full_path, "temp")
    assert fs_manager.nas_write.get_temp_path() == expected_path

def test_nas_high_speed_model_path(fs_manager):
    annotation_class_id = 4
    expected_path = os.path.join(
        fs_manager.nas_high_speed.full_path, "classes", f"class_{annotation_class_id}"
    )
    assert fs_manager.nas_high_speed.get_high_speed_model_path(annotation_class_id) == expected_path