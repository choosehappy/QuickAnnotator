"""
Filesystem-based dataset wrapper for improved-v2 research workflow.

This module provides a minimal FilesystemDataset that loads images from local
PNG files, which is then wrapped by the main production PatchedDataset for
patching and augmentation. This enables reuse of the main DL patching logic
without requiring database integration.
"""

from pathlib import Path
from typing import List, Iterator, Tuple

import cv2
import numpy as np
from torch.utils.data import IterableDataset

from quickannotator.dl.patcheddataset import PatchedDataset


class FilesystemDataset(IterableDataset):
    """
    Simple dataset that loads images and masks from filesystem PNG files.
    
    Designed to be wrapped by PatchedDataset for patching and augmentation.
    Mimics the interface of TileDataset but loads from local files instead of DB.
    """

    def __init__(self, img_paths: List[str], mask_paths: List[str]):
        """
        Initialize the filesystem dataset.

        Args:
            img_paths: List of paths to input images (*_img.png).
            mask_paths: List of paths to corresponding masks (*_mask.png).

        Raises:
            ValueError: If img_paths and mask_paths have different lengths.
        """
        if len(img_paths) != len(mask_paths):
            raise ValueError("img_paths and mask_paths must have the same length")

        self.img_paths = [Path(p) for p in img_paths]
        self.mask_paths = [Path(p) for p in mask_paths]

    def __iter__(self) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """
        Iterate over image-mask pairs.

        Yields:
            Tuple of (image, mask) where:
                - image: numpy array of shape (H, W, 3) in RGB, dtype uint8
                - mask: numpy array of shape (H, W), binary (0 or 1), dtype uint8
        """
        for img_path, mask_path in zip(self.img_paths, self.mask_paths):
            # Load image
            if not img_path.exists():
                raise FileNotFoundError(f"Image file not found: {img_path}")
            
            img = cv2.imread(str(img_path))
            if img is None:
                raise ValueError(f"Failed to load image: {img_path}")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Load mask
            if not mask_path.exists():
                raise FileNotFoundError(f"Mask file not found: {mask_path}")
            
            mask = cv2.imread(str(mask_path), 0)
            if mask is None:
                raise ValueError(f"Failed to load mask: {mask_path}")
            
            # Ensure mask is binary
            mask = (mask > 0).astype(np.uint8)

            yield img, mask
