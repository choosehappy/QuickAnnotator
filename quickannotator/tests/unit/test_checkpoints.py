import os
import shutil
import tempfile
import time
import quickannotator.constants as constants
from quickannotator.db.fsmanager import fsmanager

def setup_checkpoint_dir(annotation_class_id):
    # Create a temp dir and patch fsmanager to use it
    temp_dir = tempfile.mkdtemp()
    orig_base = fsmanager.nas_write.base_path
    fsmanager.nas_write.base_path = temp_dir
    yield temp_dir
    fsmanager.nas_write.base_path = orig_base
    shutil.rmtree(temp_dir)


def test_get_new_checkpoint_filepath_and_latest():
    annotation_class_id = 456
    with tempfile.TemporaryDirectory() as temp_dir:
        orig_base = fsmanager.nas_write.base_path
        fsmanager.nas_write.base_path = temp_dir
        # Create 3 fake checkpoints
        paths = []
        for i in range(3):
            path = fsmanager.nas_write.get_new_checkpoint_filepath(annotation_class_id)
            with open(path, 'w') as f:
                f.write(f"ckpt {i}")
            time.sleep(0.01)  # Ensure different ctime
            paths.append(path)
        latest = fsmanager.nas_write.get_latest_checkpoint_filepath(annotation_class_id)
        assert os.path.basename(latest) == os.path.basename(paths[-1])
        fsmanager.nas_write.base_path = orig_base

def test_truncate_checkpoints():
    annotation_class_id = 789
    with tempfile.TemporaryDirectory() as temp_dir:
        orig_base = fsmanager.nas_write.base_path
        fsmanager.nas_write.base_path = temp_dir
        # Create 7 fake checkpoints
        paths = []
        for i in range(7):
            path = fsmanager.nas_write.get_new_checkpoint_filepath(annotation_class_id)
            with open(path, 'w') as f:
                f.write(f"ckpt {i}")
            time.sleep(2)
            paths.append(path)
        fsmanager.nas_write.truncate_checkpoints(annotation_class_id, max_checkpoints=5)
        savepath = fsmanager.nas_write.get_class_checkpoint_path(annotation_class_id)
        files = [f for f in os.listdir(savepath) if f.endswith(constants.CHECKPOINT_FILENAME)]
        assert len(files) == 5
        fsmanager.nas_write.base_path = orig_base


def test_get_all_checkpoint_filenames():
    annotation_class_id = 101
    with tempfile.TemporaryDirectory() as temp_dir:
        orig_base = fsmanager.nas_write.base_path
        orig_full_path = fsmanager.nas_write.full_path
        fsmanager.nas_write.base_path = temp_dir
        fsmanager.nas_write.full_path = os.path.join(temp_dir, "nas_write")
        # Test with no checkpoints
        filenames = fsmanager.nas_write.get_all_checkpoint_filenames(annotation_class_id)
        assert filenames == []
        # Create 4 fake checkpoints with unique timestamps
        checkpoint_names = [
            "20260101_10-00-00_model.safetensors",
            "20260102_11-00-00_model.safetensors",
            "20260103_12-00-00_model.safetensors",
            "20260104_13-00-00_model.safetensors",
        ]
        savepath = fsmanager.nas_write.get_class_checkpoint_path(annotation_class_id)
        os.makedirs(savepath, exist_ok=True)
        for name in checkpoint_names:
            path = os.path.join(savepath, name)
            with open(path, 'w') as f:
                f.write(f"ckpt {name}")
        filenames = fsmanager.nas_write.get_all_checkpoint_filenames(annotation_class_id)
        assert len(filenames) == 4
        assert filenames == sorted(filenames, reverse=True)
        assert checkpoint_names[-1] == filenames[0]
        fsmanager.nas_write.base_path = orig_base
        fsmanager.nas_write.full_path = orig_full_path


def test_get_checkpoint_filepath_by_filename():
    annotation_class_id = 102
    with tempfile.TemporaryDirectory() as temp_dir:
        orig_base = fsmanager.nas_write.base_path
        orig_full_path = fsmanager.nas_write.full_path
        fsmanager.nas_write.base_path = temp_dir
        fsmanager.nas_write.full_path = os.path.join(temp_dir, "nas_write")
        # Test with no checkpoints directory
        filepath = fsmanager.nas_write.get_checkpoint_filepath_by_filename(annotation_class_id, "20260101_10-00-00_model.safetensors")
        assert filepath is None
        # Create a fake checkpoint
        checkpoint_name = "20260101_10-00-00_model.safetensors"
        savepath = fsmanager.nas_write.get_class_checkpoint_path(annotation_class_id)
        os.makedirs(savepath, exist_ok=True)
        path = os.path.join(savepath, checkpoint_name)
        with open(path, 'w') as f:
            f.write("ckpt")
        # Test finding existing checkpoint
        filepath = fsmanager.nas_write.get_checkpoint_filepath_by_filename(annotation_class_id, checkpoint_name)
        assert filepath == path
        # Test with non-existent filename
        filepath = fsmanager.nas_write.get_checkpoint_filepath_by_filename(annotation_class_id, "20260102_10-00-00_model.safetensors")
        assert filepath is None
        fsmanager.nas_write.base_path = orig_base
        fsmanager.nas_write.full_path = orig_full_path
