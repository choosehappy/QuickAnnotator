import large_image
from pymemcache.client.base import PooledClient
from pymemcache import serde
import os, io 
from PIL import Image as PILImage
import numpy as np
from quickannotator.constants import ImageFormat
from quickannotator.db import get_session
from quickannotator.db.fsmanager import fsmanager
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Generic, Optional

from quickannotator.db.models import Image, AnnotationClass
from quickannotator.api.v1.utils.coordinate_space import TileSpace
import quickannotator.constants as constants
import logging

logger = logging.getLogger(constants.LoggerNames.RAY.value)

def compress_to_image_bytestream(matrix: np.ndarray, format: ImageFormat, **kwargs):
    """
    Compress a NumPy matrix to an image bytestream.

    Args:
        matrix (np.ndarray): The image data as a NumPy array.
        format (ImageFormat): The format to save the image (PNG or JPG).
        **kwargs: Additional arguments for the PIL save method.

    Returns:
        bytes: The compressed image as a bytestream.
    """
    # Convert NumPy matrix to a PIL Image
    image = PILImage.fromarray(matrix.astype(np.uint8))
    # Save the image to a BytesIO object
    with io.BytesIO() as output:
        image.save(output, format=format.value, **kwargs)
        bytestream = output.getvalue()  # Get the byte data
    return bytestream

# Function to decompress JPEG bytes back to a NumPy array
def decompress_from_image_bytestream(bytestream):
    # Open the byte data as an image using PIL
    with io.BytesIO(bytestream) as input:
        image = PILImage.open(input)
        # Convert image back to NumPy array
        matrix = np.array(image)
    return matrix


def load_tile(tile): #TODO: i suspect this sort of function exists elsewhere within QA to serve tiles to the front end? change to merge functionality?
    with get_session() as db_session:
        image = db_session.query(Image).filter_by(id=tile.image_id).first()
        annoclass = db_session.query(AnnotationClass).filter_by(id=tile.annotation_class_id).first()
        db_session.expunge_all()

    image_path = image.path
    fullpath = fsmanager.nas_read.relative_to_global(image_path)
    li = large_image.getTileSource(fullpath)


    #---- two options here
    sizeXtargetmag, sizeYtargetmag= li.getPointAtAnotherScale((li.sizeX,li.sizeY), #TODO: should this be modfieid somehow to not use Large image?
                                                                targetScale={'magnification': annoclass.work_mag}, 
                                                                targetUnits='mag_pixels') 
    
    #x,y=tileid_to_point(tile.tile_size,sizeXtargetmag,sizeYtargetmag,tile.tile_id)   #REFACTORED --- if working, delete this comment

    ts = TileSpace(annoclass.work_tilesize, sizeXtargetmag, sizeYtargetmag)
    x,y = ts.tileid_to_point(tile.tile_id) 

    region, _ = li.getRegion(region=dict(left=x, top=y, width=annoclass.work_tilesize, height=annoclass.work_tilesize,units='pixels'), 
                                            scale={'magnification':annoclass.work_mag},format=large_image.tilesource.TILE_FORMAT_NUMPY)

    io_image = region[:,:,:3] #np.array(region.convert("RGB"))


    # Get actual height and width
    actual_height, actual_width, _ = io_image.shape

    # Compute padding amounts
    pad_height = max(0, annoclass.work_tilesize - actual_height)
    pad_width = max(0, annoclass.work_tilesize - actual_width)

    # Apply padding (black is default since mode='constant' and constant_values=0)
    io_image = np.pad(io_image, 
                    ((0, pad_height), (0, pad_width), (0, 0)), 
                    mode='constant', 
                    constant_values=0)
    
    return io_image,x,y


#-----
class CacheableObject(ABC):
    """
    Abstract base class for cacheable objects.

    This class serves as a base for objects that can be cached, such as images and masks.
    It defines the structure and common functionality for cacheable objects.
    """

    @staticmethod
    @abstractmethod
    def get_key(*args, **kwargs) -> str:
        """
        Returns a unique key for the cacheable object based on image and tile identifiers.

        Args:
            image_id (int): The ID of the image.
            tile_id (int): The ID of the tile.

        Returns:
            str: The unique key for the cacheable object.
        """
        pass


class CacheableImage(CacheableObject):
    def __init__(self, matrix: np.ndarray, coordinates: tuple[int]):
        if not isinstance(matrix, np.ndarray):
            raise TypeError("Matrix must be a NumPy array")
        if matrix.ndim != 3 or matrix.shape[2] != 3:
            raise ValueError("Matrix must be a 3D array with 3 channels (RGB)")
        self.image = compress_to_image_bytestream(matrix, format=constants.ImageFormat.JPG, quality=95)
        self.coordinates = coordinates

    def get_image(self):
        """
        Returns the uncompressed image data.
        """
        return decompress_from_image_bytestream(self.image)
    
    def get_coordinates(self):
        """
        Returns the coordinates of the image.
        """
        return self.coordinates
    
    @staticmethod
    def get_key(image_id: int, tile_id: int) -> str:
        """
        Returns a unique key for the cacheable image based on image and tile identifiers.

        Args:
            image_id (int): The ID of the image.
            tile_id (int): The ID of the tile.

        Returns:
            str: The unique key for the cacheable image.
        """
        return f"image:{image_id}:{tile_id}"


class CacheableMask(CacheableObject):
    def __init__(self, matrix: np.ndarray, weight: np.ndarray):
        if matrix.dtype != np.uint8:
            raise ValueError("Matrix must have dtype of uint8")
        if weight.dtype != np.uint8:
            raise ValueError("Weight must have dtype of uint8")
        self.mask = compress_to_image_bytestream(matrix, format=constants.ImageFormat.PNG)
        self.weight = compress_to_image_bytestream(weight, format=constants.ImageFormat.PNG)

    def get_mask(self):
        """
        Returns the uncompressed mask data.
        """
        return decompress_from_image_bytestream(self.mask)
    

    def get_weight(self):
        """
        Returns the weight of the mask.
        """
        return decompress_from_image_bytestream(self.weight)
    

    @staticmethod
    def get_key(image_id: int, annotation_class_id: int, tile_id: int) -> str:
        """
        Returns a unique key for the cacheable mask based on image and tile identifiers.

        Args:
            image_id (int): The ID of the image.
            tile_id (int): The ID of the tile.

        Returns:
            str: The unique key for the cacheable mask.
        """
        return f"mask:{image_id}:{annotation_class_id}:{tile_id}"


T = TypeVar('T', bound=CacheableObject)


class CacheManager(ABC, Generic[T]):
    """
    Abstract base class for managing cache storage and retrieval of objects.

    This class provides a generic interface for caching objects using a key-value 
    storage backend (e.g., Memcached). It defines the structure and common 
    functionality for caching, retrieving, and invalidating cache entries.

    Subclasses must set the `cached_object_class` attribute to define the type of objects being cached.
    """

    cached_object_class: Type[T] = None  # To be set by subclasses

    def __init__(self, client=None):
        """
        Initialize the CacheManager with a memcached client.

        Args:
            client (PooledClient, optional): A memcached client instance. If not provided, a default client is created.
        """
        self.client = client or self.get_memcached_client()

    @staticmethod
    def get_memcached_client():
        """
        Returns a configured memcached client instance.

        Returns:
            PooledClient: A memcached client configured with the application's constants.
        """
        try:
            client = PooledClient((constants.MEMCACHED_HOST, constants.MEMCACHED_PORT), 
                                  serde=serde.pickle_serde, 
                                  max_pool_size=constants.MAX_POOL_SIZE)
            logger.info("Memcached client successfully created.")
            return client
        except Exception as e:
            logger.error(f"Failed to create Memcached client: {e}")
            return None

    def cache(self, key: str, data: T, expire: int = 3600):
        """
        Cache data using a key.

        Args:
            key (str): The cache key.
            data (T): The data to cache.
            expire (int, optional): Time-to-live for the cached data in seconds. Defaults to 3600 seconds (1 hour).
        """
        try:
            if not isinstance(data, self.cached_object_class):
                raise TypeError(f"Data must be an instance of {self.cached_object_class.__name__}")
            self.client.set(key, data, expire)
            logger.info(f"Data cached successfully with key: {key}")
        except Exception as e:
            logger.error(f"Failed to cache data with key {key}: {e}. Continuing without cache.")

    def get_cached(self, key: str) -> Optional[T]:
        """
        Retrieve cached data using a key.

        Args:
            key (str): The cache key.

        Returns:
            Optional[T]: The cached data, or None if the key does not exist in the cache.
        """
        try:
            cached_data = self.client.get(key)
            if cached_data is not None and not isinstance(cached_data, self.cached_object_class):
                raise TypeError(f"Cached data is not an instance of {self.cached_object_class.__name__}")
            logger.info(f"Cache hit for key: {key}")
            return cached_data
        except Exception as e:
            logger.warning(f"Cache retrieval failed for key {key}: {e}. Proceeding without cache.")
            return None

    def invalidate(self, key: str):
        """
        Invalidate cached data using a key.

        Args:
            key (str): The cache key.
        """
        try:
            self.client.delete(key)
            logger.info(f"Cache invalidated for key: {key}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache for key {key}: {e}. Continuing without invalidation.")
            return


class ImageCacheManager(CacheManager[CacheableImage]):
    cached_object_class = CacheableImage


class MaskCacheManager(CacheManager[CacheableMask]):
    cached_object_class = CacheableMask

