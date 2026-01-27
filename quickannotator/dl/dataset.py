import shapely.wkb
import cv2, numpy as np

import scipy.ndimage
from torch.utils.data import IterableDataset
from quickannotator.db import get_session
from quickannotator.db.crud.tile import TileStoreFactory
from quickannotator.db.crud.annotation_class import get_annotation_class_by_id
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.dl.utils import MaskCacheManager, ImageCacheManager, CacheableImage, CacheableMask, load_tile 
from skimage.measure import label, regionprops
import logging
import os
from datetime import datetime
import quickannotator.constants as constants

logger = logging.getLogger(constants.LoggerNames.RAY.value)

class TileDataset(IterableDataset):
    def __init__(self, classid, transforms=None, edge_weight=0, boost_count=5):
        self.classid = classid
        self.transforms = transforms
        self.edge_weight = edge_weight
        self.boost_count = boost_count
        self.image_cache_manager = ImageCacheManager()
        self.mask_cache_manager = MaskCacheManager()
        with get_session() as db_session:  # Ensure this provides a session context
            annotation_class = get_annotation_class_by_id(classid)
            self.magnification = annotation_class.work_mag
            self.tile_size = annotation_class.work_tilesize
        
        

    def __iter__(self):
        tilestore = TileStoreFactory.get_tilestore()
        
        while tile := tilestore.get_workers_tiles(self.classid, self.boost_count):
            #print(tile)
            #print(f"tile retval 2 {tile}")

            image_id = tile.image_id
            tile_id = tile.tile_id
            img_cache_key = CacheableImage.get_key(image_id, self.classid, tile_id)
            img_cache_val = self.image_cache_manager.get_cached(img_cache_key)
            mask_cache_key = CacheableMask.get_key(image_id, self.classid, tile_id)
            mask_cache_val = self.mask_cache_manager.get_cached(mask_cache_key)

            


            if img_cache_val:
                io_image = img_cache_val.get_image()
                x,y = img_cache_val.get_coordinates()
            else:
                io_image,x,y = load_tile(tile)
                
                self.image_cache_manager.cache(img_cache_key, CacheableImage(io_image, (x, y)))
            

            if mask_cache_val:
                mask_image, weight = mask_cache_val.get_mask(), mask_cache_val.get_weight()
            else:
                with get_session() as db_session: #TODO: Move down?
                    store = AnnotationStore(image_id, self.classid, is_gt=True, in_work_mag=True, mode=constants.AnnotationReturnMode.WKB)
                    annotations = store.get_annotations_for_tiles(tile_id)
                    db_session.expunge_all()

                    if len(annotations) == 0: # would be strange given how things are set up?
                        continue
            #----
                mask_image = np.zeros((self.tile_size, self.tile_size), dtype=np.uint8) #TODO: maybe should be moved to a project wide available utility function? not sure
                for annotation in annotations:
                    annotation_polygon = shapely.wkb.loads(bytes(annotation.polygon.data))
                    translated_polygon = shapely.affinity.translate(annotation_polygon, xoff=-x, yoff=-y) # need to scale this down from base mag to target mag
                    cv2.fillPoly(mask_image, [np.array(translated_polygon.exterior.coords, dtype=np.int32)], 1)
                
                
                mask_image = (mask_image>0).astype(np.uint8) # if two polygons slightly overlap, fillpoly is addiditve and you end upwith values >1
                
                if self.edge_weight:
                    weight = scipy.ndimage.morphology.binary_dilation(mask_image, iterations=2) & ~mask_image
                else:
                    weight = np.ones(mask_image.shape, dtype=mask_image.dtype)
                
                self.mask_cache_manager.cache(mask_cache_key, CacheableMask(mask_image, weight))

            img_new = io_image
            mask_new = mask_image
            weight_new = weight

            if self.transforms:
                augmented = self.transforms(image=io_image, masks=[mask_image, weight])
                img_new = augmented['image']
                mask_new, weight_new = augmented['masks']

            # Save the image, mask, and weight to files
            base_path = "/opt/QuickAnnotator/quickannotator/mounts/nas_write"
            os.makedirs(base_path, exist_ok=True)



            # Log image dimensions
            logger.info(f"Image dimensions: {img_new.shape}, Mask dimensions: {mask_new.shape}, Weight dimensions: {weight_new.shape}")

            # Save the image, mask, and weight to files

            # image_path = os.path.join(base_path, f"image_{image_id}_class_{self.classid}_tile_{tile_id}.png")
            # mask_path = os.path.join(base_path, f"mask_{image_id}_class_{self.classid}_tile_{tile_id}.png")
            # weight_path = os.path.join(base_path, f"weight_{image_id}_class_{self.classid}_tile_{tile_id}.png")
            # cv2.imwrite(image_path, io_image)
            # cv2.imwrite(mask_path, mask_image * 255)  # Scale mask to 0-255 for saving
            # cv2.imwrite(weight_path, weight * 255)  # Scale weight to 0-255 for saving

            yield img_new, mask_new[None,::], weight_new


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
    
    def __init__(self, tile_dataset: TileDataset, patch_size: int = 512, transforms=None):
        """
        Initialize PatchedDataset wrapper.
        
        Args:
            tile_dataset: TileDataset instance to wrap
            patch_size: Size of patches to extract from tiles (default 512x512)
            transforms: Optional augmentation transforms to apply to patches
        """
        self.tile_dataset = tile_dataset
        self.patch_size = patch_size
        self.transforms = transforms
        
    def _extract_patches(self, image: np.ndarray, mask: np.ndarray, weight: np.ndarray):
        """
        Extract non-overlapping patches from a tile along with their masks and weights.
        
        Args:
            image: Full tile image of shape (H, W, C)
            mask: Binary mask of shape (H, W)
            weight: Weight map of shape (H, W)
            
        Yields:
            Tuples of (patch_image, patch_mask, patch_weight, hv_map)
        """
        h, w = mask.shape
        
        # Extract non-overlapping patches
        for y in range(0, h - self.patch_size + 1, self.patch_size):
            for x in range(0, w - self.patch_size + 1, self.patch_size):
                # Extract patch regions
                patch_img = image[y:y+self.patch_size, x:x+self.patch_size]
                patch_mask = mask[y:y+self.patch_size, x:x+self.patch_size]
                patch_weight = weight[y:y+self.patch_size, x:x+self.patch_size]
                
                # Only yield patches with sufficient mask coverage
                if patch_mask.sum() > 0:
                    # Compute HV map for this patch
                    hv_map = compute_hv_map(patch_mask)
                    
                    # Apply transforms if provided
                    if self.transforms:
                        augmented = self.transforms(
                            image=patch_img, 
                            masks=[patch_mask, patch_weight, hv_map]
                        )
                        patch_img = augmented['image']
                        patch_mask, patch_weight, hv_map = augmented['masks']
                    
                    yield patch_img, patch_mask[None, ::], patch_weight, hv_map[None, ::]
    
    def __iter__(self):
        """
        Iterate over patches extracted from tiles.
        
        Yields:
            Tuples of (patch_image, patch_mask, patch_weight, hv_map)
        """
        for tile_image, tile_mask, tile_weight in self.tile_dataset:
            # Extract patches from the tile
            # Note: tile_mask and tile_weight come with shape (1, H, W) from TileDataset
            tile_mask_2d = tile_mask[0]
            tile_weight_2d = tile_weight
            
            # Extract and yield patches
            for patch_data in self._extract_patches(tile_image, tile_mask_2d, tile_weight_2d):
                yield patch_data