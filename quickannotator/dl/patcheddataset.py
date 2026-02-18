import random
import numpy as np
from skimage.measure import label, regionprops
from torch.utils.data import IterableDataset


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


class PatchedDataset(IterableDataset):
    """
    Wrapper around TileDataset that converts expensive Tiles into patches.
    
    This dataset wraps TileDataset and receives Tiles from it. For each Tile,
    it extracts multiple 512x512 patches with corresponding HV (hypervector) maps,
    avoiding redundant Tile fetches.
    """
    
    def __init__(self, tile_dataset: IterableDataset, patch_size: int = 512, stride: int = 256, shuffle_patches: bool = True, transforms=None):
        """
        Initialize PatchedDataset wrapper.
        
        Args:
            tile_dataset: IterableDataset instance to wrap
            patch_size: Size of patches to extract from tiles (default 512x512)
            stride: Stride for sliding window extraction (default 256 for 50% overlap)
            shuffle_patches: Whether to shuffle patches from each tile (default True)
            transforms: Optional augmentation transforms to apply to patches
        """
        self.tile_dataset = tile_dataset
        self.patch_size = patch_size
        self.stride = stride
        self.shuffle_patches = shuffle_patches
        self.transforms = transforms
        
    def _get_candidate_patches(self, mask: np.ndarray):
        """
        Generate valid patch coordinates, with optional shuffling.
        
        Handles both streaming (yields immediately) and buffering+shuffling strategies.
        
        Args:
            mask: Binary mask of shape (H, W)
            
        Yields:
            Tuples of (y, x) coordinates for valid patches
        """
        h, w = mask.shape
        candidates = []
        
        # Collect valid patch coordinates
        for y in range(0, h - self.patch_size + 1, self.stride):
            for x in range(0, w - self.patch_size + 1, self.stride):
                if mask[y:y+self.patch_size, x:x+self.patch_size].sum() > 0:
                    candidates.append((y, x))
        
        # Shuffle if requested, otherwise yield in order
        if self.shuffle_patches:
            random.shuffle(candidates)
        
        yield from candidates
    
    def _extract_patches(self, image: np.ndarray, mask: np.ndarray):
        """
        Extract patches from a tile along with their masks using sliding window.
        
        Supports both streaming (memory efficient) and shuffled (better randomization) modes.
        Switch with shuffle_patches parameter.
        
        Args:
            image: Full tile image of shape (H, W, C)
            mask: Binary mask of shape (H, W)
            
        Yields:
            Tuples of (patch_image, patch_mask, hv_map)
        """
        for y, x in self._get_candidate_patches(mask):
            # Extract patch regions
            patch_img = image[y:y+self.patch_size, x:x+self.patch_size]
            patch_mask = mask[y:y+self.patch_size, x:x+self.patch_size]
            
            # Compute HV map for this patch
            hv_map = compute_hv_map(patch_mask)
            
            # Apply transforms if provided
            if self.transforms:
                augmented = self.transforms(
                    image=patch_img, 
                    masks=[patch_mask, hv_map]
                )
                patch_img = augmented['image']
                patch_mask, hv_map = augmented['masks']
            
            yield patch_img, patch_mask[None, ::], hv_map[None, ::]
    
    def __iter__(self):
        """
        Iterate over patches extracted from tiles.
        
        Yields:
            Tuples of (patch_image, patch_mask, hv_map)
        """
        for tile_image, tile_mask in self.tile_dataset:

            # Extract and yield patches
            for patch_data in self._extract_patches(tile_image, tile_mask):
                yield patch_data