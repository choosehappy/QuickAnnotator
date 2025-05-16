from quickannotator.db import Base, engine
from sqlalchemy import Table
from quickannotator import constants
import os
from datetime import datetime

from quickannotator.db.crud.image import get_image_by_id

def create_dynamic_model(table_name, base=Base):
    class DynamicAnnotation(base):
        __tablename__ = table_name
        __table__ = Table(table_name, base.metadata, autoload_with=engine)

    return DynamicAnnotation


def build_annotation_table_name(image_id: int, annotation_class_id: int, is_gt: bool):
    gtpred = 'gt' if is_gt else 'pred'
    table_name = f"annotation_{image_id}_{annotation_class_id}_{gtpred}"
    return table_name

def build_tarpath(image_id: int, annotation_class_id: int, is_gt: bool):
    fsman = FileSystemManager()
    project_id = get_image_by_id(image_id).project_id
    save_path = fsman.get_project_mask_path(project_id, image_id)
    tarname = build_tarname(image_id, annotation_class_id, is_gt)
    tarpath = os.path.join(save_path, tarname)
    return tarpath

def build_tarname(image_id: int, annotation_class_id: int, is_gt: bool):
    """
    Build the tar name for a given image and annotation class.

    Args:
        image_id (int): The ID of the image.
        annotation_class_id (int): The ID of the annotation class.
        is_gt (bool): Flag indicating if the annotations are ground truth.

    Returns:
        str: The tar name for the specified image and annotation class.
    """
    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    tarname = f'{table_name}.tar.gz'
    return tarname

def search_for_tarfile(tarname: str) -> str:   # TODO: add image_id for faster search?
    """
    Search for a tar file in the specified directories.

    Args:
        tarname (str): The name of the tar file to search for.

    Returns:
        str: The full path to the tar file if found, otherwise None.
    """
    fsman = FileSystemManager()
    directories = [fsman.get_nas_write()]
    
    for directory in directories:
        for root, _, files in os.walk(directory):
            if tarname in files:
                return os.path.join(root, tarname)
    
    return None


class FileSystemManager:
    """
    Manages file system paths for various operations such as accessing images, masks, 
    project files, and temporary files in the QuickAnnotator system.
    """

    def __init__(self):
        """
        Initialize the FileSystemManager with base paths for different storage types.
        """
        self.base_path = constants.BASE_PATH
        self.nas_read = os.path.join(self.base_path, "nas_read")
        self.nas_write = os.path.join(self.base_path, "nas_write")
        self.nas_high_speed = os.path.join(self.base_path, "nas_high_speed")

    def get_nas_read(self):
        """
        Get the read-only NAS path.

        Returns:
            str: The read-only NAS path.
        """
        return self.nas_read
    
    def get_nas_write(self):
        """
        Get the write-enabled NAS path.

        Returns:
            str: The write-enabled NAS path.
        """
        return self.nas_write
    
    def get_nas_high_speed(self):
        """
        Get the high-speed NAS path.

        Returns:
            str: The high-speed NAS path.
        """
        return self.nas_high_speed

    def get_input_images_path(self):
        """
        Get the directory path for whole slide images (WSIs).

        Returns:
            str: The directory path containing WSI images.
        """
        return os.path.join(self.nas_read, "images")

    def get_input_masks_dir(self):
        """
        Get the directory path for annotation masks.

        Returns:
            str: The directory path containing annotation masks.
        """
        return os.path.join(self.nas_read, "masks")

    def get_project_image_path(self, proj_id: int, img_id: int):
        """
        Get the directory path for project images.

        Args:
            proj_id (int): The project ID.
            img_id (int): The image ID.

        Returns:
            str: The directory path for the project images.
        """
        return os.path.join(self.nas_write, "projects", f"proj_{proj_id}", "images", f"img_{img_id}")

    def get_project_mask_path(self, proj_id: int, img_id: int):
        """
        Get the directory path for project masks.

        Args:
            proj_id (int): The project ID.
            img_id (int): The image ID.

        Returns:
            str: The directory path for the project masks.
        """
        return os.path.join(self.nas_write, "projects", f"proj_{proj_id}", "images", f"img_{img_id}", "masks")

    def get_class_checkpoint_path(self, annotation_class_id: int):
        """
        Get the directory path for class checkpoints.

        Args:
            annotation_class_id (int): The annotation class ID.

        Returns:
            str: The directory path for the class checkpoints.
        """
        return os.path.join(self.nas_write, "classes", f"class_{annotation_class_id}", "checkpoints")

    def get_temp_image_path(self):
        """
        Get the directory path for temporary images.

        Returns:
            str: The directory path for temporary images.
        """
        return os.path.join(self.nas_write, "temp")

    def get_high_speed_model_path(self, annotation_class_id: int):
        """
        Get the directory path for high-speed models.

        Args:
            annotation_class_id (int): The annotation class ID.

        Returns:
            str: The directory path for high-speed models.
        """
        return os.path.join(self.nas_high_speed, "classes", f"class_{annotation_class_id}")
