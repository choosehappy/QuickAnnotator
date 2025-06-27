import pytest
import numpy as np
from PIL import Image

# filepath: /opt/QuickAnnotator/quickannotator/tests/unit/test_utils.py
from quickannotator.dl.utils import (
    CacheableImage,
    CacheableMask,
    ImageCacheManager,
    MaskCacheManager,
)


def test_image_cache_manager():
    # Initialize ImageCacheManager
    manager = ImageCacheManager()

    # Create a sample image matrix
    matrix = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    coordinates = (10, 20)
    image = CacheableImage(matrix, coordinates)

    # Generate a cache key
    key = CacheableImage.get_key(image_id=1, tile_id=1)

    # Cache the image
    manager.cache(key, image)

    # Retrieve the cached image
    cached_image = manager.get_cached(key)
    assert cached_image is not None

    # Check if the retrieved image is close to the original (accounting for lossy compression)
    assert np.isclose(np.sum(cached_image.get_image()), np.sum(matrix), atol=1000)
    assert cached_image.get_coordinates() == coordinates

    # Invalidate the cache
    manager.invalidate(key)
    assert manager.get_cached(key) is None


def test_mask_cache_manager():
    # Initialize MaskCacheManager
    manager = MaskCacheManager()

    # Create a sample mask matrix and weight matrix
    matrix = np.random.randint(0, 2, (100, 100), dtype=np.uint8)
    weight = np.random.randint(0, 2, (100, 100), dtype=np.uint8)
    mask = CacheableMask(matrix, weight)

    # Generate a cache key
    key = CacheableMask.get_key(image_id=1, annotation_class_id=1, tile_id=1)

    # Cache the mask
    manager.cache(key, mask)

    # Retrieve the cached mask
    cached_mask = manager.get_cached(key)
    assert cached_mask is not None
    assert np.array_equal(cached_mask.get_mask(), matrix)
    assert np.array_equal(cached_mask.get_weight(), weight)

    # Invalidate the cache
    manager.invalidate(key)
    assert manager.get_cached(key) is None