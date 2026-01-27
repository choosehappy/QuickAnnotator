"""
Utility functions for image processing and data preparation.

This module contains helper functions for computing hypervector maps,
edge detection, and other preprocessing tasks.
"""

import numpy as np
from skimage.measure import label, regionprops


def compute_hv_map(mask_img: np.ndarray) -> np.ndarray:
    """
    Compute hypervector (HV) map from a binary mask.

    The HV map represents distances from object centroids, normalized per object.

    Args:
        mask_img: Binary mask as numpy array of shape (H, W).

    Returns:
        HV map as float32 array of shape (H, W).
    """
    hv_img = np.zeros_like(mask_img, dtype=np.float32)

    # Compute hypervector distances for hv_img
    for rg in regionprops(label(mask_img)):
        centroid = np.array(rg.centroid)
        coords = rg.coords
        distances = np.linalg.norm(coords - centroid, axis=1)
        distances = (distances + 10) ** 2
        distances /= distances.max()  # Normalize to [0, 1]
        for (coord, dist) in zip(coords, distances):
            hv_img[tuple(coord)] = dist

    return hv_img