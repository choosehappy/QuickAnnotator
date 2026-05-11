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

def test_get_checkpoint_filepath():
    annotation_class_id = 123
    with tempfile.TemporaryDirectory() as temp_dir:
        orig_base = fsmanager.nas_write.base_path
        fsmanager.nas_write.base_path = temp_dir
        path = fsmanager.nas_write.get_checkpoint_filepath(annotation_class_id)
        assert os.path.basename(path) == constants.CHECKPOINT_FILENAME
        assert os.path.exists(os.path.dirname(path))
        fsmanager.nas_write.base_path = orig_base

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
            time.sleep(0.01)
            paths.append(path)
        fsmanager.nas_write.truncate_checkpoints(annotation_class_id, max_checkpoints=5)
        savepath = fsmanager.nas_write.get_class_checkpoint_path(annotation_class_id)
        files = [f for f in os.listdir(savepath) if f.endswith(constants.CHECKPOINT_FILENAME)]
        assert len(files) == 5
        fsmanager.nas_write.base_path = orig_base
