"""
Dataset classes for patched segmentation training.

This module provides datasets for loading and preprocessing image patches
with masks and hypervector maps for weakly supervised segmentation.
"""

import random
from pathlib import Path
from typing import List, Optional, Tuple, Iterator

import cv2
import numpy as np
import torch
from torch.utils.data import IterableDataset

from utils import compute_hv_map


class PatchedSegmentationDataset(IterableDataset):
    """
    Iterable dataset for patched segmentation with active learning.

    Loads images and masks, patches them into fixed-size patches, computes HV maps,
    and applies augmentations. Filters patches by minimum positive pixels.
    """

    def __init__(
        self,
        img_paths: List[str],
        mask_paths: List[str],
        patch_size: int = 512,
        stride: int = 256,
        min_positive_pixels: int = 16,
        max_patches_per_image: Optional[int] = None,
        shuffle_patches: bool = True,
        transforms: Optional[object] = None
    ):
        """
        Initialize the dataset.

        Args:
            img_paths: List of paths to input images.
            mask_paths: List of paths to corresponding masks.
            patch_size: Size of each patch (square).
            stride: Stride for patching (overlap = patch_size - stride).
            min_positive_pixels: Minimum positive pixels required in a patch.
            max_patches_per_image: Maximum patches per image per epoch (None for all).
            shuffle_patches: Whether to shuffle patch order.
            transforms: Albumentations transform pipeline.

        Raises:
            ValueError: If img_paths and mask_paths have different lengths.
        """
        if len(img_paths) != len(mask_paths):
            raise ValueError("img_paths and mask_paths must have the same length")

        self.img_paths = [Path(p) for p in img_paths]
        self.mask_paths = [Path(p) for p in mask_paths]
        self.patch_size = patch_size
        self.stride = stride
        self.min_positive_pixels = min_positive_pixels
        self.max_patches_per_image = max_patches_per_image
        self.shuffle_patches = shuffle_patches
        self.transforms = transforms

    def __iter__(self) -> Iterator[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
        """
        Iterate over patches.

        Yields:
            Tuple of (image_patch, mask_patch, hv_patch).
        """
        worker_info = torch.utils.data.get_worker_info()
        if worker_info is None:
            # Single-process
            img_paths = self.img_paths
            mask_paths = self.mask_paths
        else:
            # Split workload across workers
            per_worker = int(np.ceil(len(self.img_paths) / worker_info.num_workers))
            start = worker_info.id * per_worker
            end = min(start + per_worker, len(self.img_paths))
            img_paths = self.img_paths[start:end]
            mask_paths = self.mask_paths[start:end]

        for img_path, mask_path in zip(img_paths, mask_paths):
            # Load image and mask with error handling
            if not img_path.exists():
                raise FileNotFoundError(f"Image file not found: {img_path}")
            if not mask_path.exists():
                raise FileNotFoundError(f"Mask file not found: {mask_path}")

            img = cv2.imread(str(img_path))
            if img is None:
                raise ValueError(f"Failed to load image: {img_path}")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  

            mask = cv2.imread(str(mask_path), 0)
            if mask is None:
                raise ValueError(f"Failed to load mask: {mask_path}")

            hv = compute_hv_map(mask)

            H, W = mask.shape
            ps = self.patch_size

            # Collect candidate patches
            candidates = []
            ys = range(0, H - ps + 1, self.stride)
            xs = range(0, W - ps + 1, self.stride)
            for y in ys:
                for x in xs:
                    if mask[y:y+ps, x:x+ps].sum() >= self.min_positive_pixels:
                        candidates.append((y, x))

            # Fallback if no positive patches
            if len(candidates) == 0:
                y = np.random.randint(0, H - ps + 1)
                x = np.random.randint(0, W - ps + 1)
                candidates = [(y, x)]

            # Shuffle patches if requested
            if self.shuffle_patches:
                random.shuffle(candidates)

            # Limit patches per image
            if self.max_patches_per_image is not None:
                candidates = candidates[:self.max_patches_per_image]

            # Yield patches one by one
            for y, x in candidates:
                img_patch = img[y:y+ps, x:x+ps]          # (H, W, C) uint8
                mask_patch = mask[y:y+ps, x:x+ps]        # (H, W)
                hv_patch = hv[y:y+ps, x:x+ps]            # (H, W)

                if self.transforms:
                    augmented = self.transforms(image=img_patch, masks=[mask_patch, hv_patch])
                    img_patch = augmented['image']
                    mask_patch, hv_patch = augmented['masks']

                # Ensure consistent shapes: img (C, H, W), masks (1, H, W)
                yield img_patch, mask_patch[None, :, :], hv_patch[None, :, :]