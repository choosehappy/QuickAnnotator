from quickannotator import constants
import os


class FileStore():
    """
    Abstract base class for managing paths in the QuickAnnotator system.
    """

    def __init__(self, sub_path: str):
        """
        Initialize the PathStore with a base path.
        """
        self.base_path = constants.MOUNTS_PATH
        self.full_path = os.path.join(self.base_path, sub_path)

    def get_base_path(self):
        """
        Get the base path for the file system.

        Returns:
            str: The base path for the file system.
        """
        return self.base_path

    def global_to_relative(self, path: str) -> str:
        """
        Convert a global path to a relative path.

        Args:
            path (str): The global path to convert.

        Returns:
            str: The relative path.
        """
        return os.path.relpath(path, start=self.full_path)

    def relative_to_global(self, path: str) -> str:
        """
        Convert a relative path to a global path. The relative path is assumed to be with respect to the base path.

        Args:
            path (str): The relative path to convert.

        Returns:
            str: The global path.
        """
        return os.path.join(self.full_path, path)

    def get_full_path(self, filepath: str = None) -> str:
        """
        Get the full path for the file system.

        Returns:
            str: The full path for the file system.
        """
        return self.full_path


class NASRead(FileStore):
    """
    Class for managing read-only paths in the QuickAnnotator system.
    """

    def __init__(self):
        """
        Initialize the NASRead with a base path.
        """
        super().__init__("nas_read")

    def get_input_images_path(self, relative: bool = False):
        """
        Get the directory path for whole slide images (WSIs).

        Args:
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path containing WSI images.
        """
        relative_path = "images"  # Removed os.path.join
        return relative_path if relative else self.relative_to_global(relative_path)

    def get_input_masks_dir(self, relative: bool = False):
        """
        Get the directory path for annotation masks.

        Args:
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path containing annotation masks.
        """
        relative_path = "masks"  # Removed os.path.join
        return relative_path if relative else self.relative_to_global(relative_path)


class NASWrite(FileStore):
    """
    Class for managing write-enabled paths in the QuickAnnotator system.
    """

    def __init__(self):
        """
        Initialize the NASWrite with a base path.
        """
        super().__init__("nas_write")

    def get_project_path(self, project_id: int, relative: bool = False):
        """
        Get the directory path for a project.

        Args:
            project_id (int): The project ID.
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path for the project.
        """
        relative_path = os.path.join("projects", f"proj_{project_id}")
        return relative_path if relative else self.relative_to_global(relative_path)

    def get_project_image_path(self, project_id: int, image_id: int, relative: bool = False):
        """
        Get the directory path for project images.

        Args:
            proj_id (int): The project ID.
            img_id (int): The image ID.
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path for the project images.
        """
        relative_path = os.path.join("projects", f"proj_{project_id}", "images", f"img_{image_id}")
        return relative_path if relative else self.relative_to_global(relative_path)

    def get_project_mask_path(self, project_id: int, image_id: int, relative: bool = False):
        """
        Get the directory path for project masks.

        Args:
            proj_id (int): The project ID.
            img_id (int): The image ID.
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path for the project masks.
        """
        relative_path = os.path.join(self.get_project_image_path(project_id, image_id, relative=True), "masks")
        return relative_path if relative else self.relative_to_global(relative_path)
    

    def get_annotation_class_path(self, annotation_class_id: int, relative: bool = False):
        """
        Get the directory path for an annotation class.

        Args:
            annotation_class_id (int): The annotation class ID.
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path for the annotation class.
        """
        relative_path = os.path.join("classes", f"class_{annotation_class_id}")
        return relative_path if relative else self.relative_to_global(relative_path)

    def get_class_checkpoint_path(self, annotation_class_id: int, relative: bool = False):
        """
        Get the directory path for class checkpoints.

        Args:
            annotation_class_id (int): The annotation class ID.
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path for the class checkpoints.
        """
        relative_path = os.path.join(self.get_annotation_class_path(annotation_class_id, relative=True), "checkpoints")
        return relative_path if relative else self.relative_to_global(relative_path)
    
    def get_logs_path(self, annotation_class_id: int, relative: bool = False):
        """
        Get the directory path for logs.

        Args:
            annotation_class_id (int): The annotation class ID.
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path for logs.
        """ 
        relative_path = os.path.join(self.get_annotation_class_path(annotation_class_id, relative=True), "logs")
        return relative_path if relative else self.relative_to_global(relative_path)

    def get_temp_image_path(self, relative: bool = False):
        """
        Get the directory path for temporary images.

        Args:
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path for temporary images.
        """
        relative_path = "temp"  # Removed os.path.join
        return relative_path if relative else self.relative_to_global(relative_path)
    
    def get_debug_path(self, relative: bool = False):
        """
        Get the directory path for debug files.

        Args:
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path for debug files.
        """
        relative_path = "debug"
        return relative_path if relative else self.relative_to_global(relative_path)


class NASHighSpeed(FileStore):
    """
    Class for managing high-speed paths in the QuickAnnotator system.
    """

    def __init__(self):
        """
        Initialize the NASHighSpeed with a base path.
        """
        super().__init__("nas_high_speed")

    def get_high_speed_model_path(self, annotation_class_id: int, relative: bool = False):
        """
        Get the directory path for high-speed models.

        Args:
            annotation_class_id (int): The annotation class ID.
            relative (bool): Whether to return a relative path.

        Returns:
            str: The directory path for high-speed models.
        """
        relative_path = os.path.join("classes", f"class_{annotation_class_id}")
        return relative_path if relative else self.relative_to_global(relative_path)


class FileSystemManager:
    """
    Manages file system paths for various operations such as accessing images, masks, 
    project files, and temporary files in the QuickAnnotator system.
    """

    def __init__(self):
        """
        Initialize the FileSystemManager with base paths for different storage types.
        """
        self.nas_read = NASRead()
        self.nas_write = NASWrite()
        self.nas_high_speed = NASHighSpeed()

    

fsmanager = FileSystemManager()