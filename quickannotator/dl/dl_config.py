"""
Configuration module for deep learning pipeline.

This module centralizes all configuration parameters for the training pipeline,
including data processing, model architecture, loss weights, and augmentation parameters.
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import albumentations as A
from albumentations.pytorch import ToTensorV2
import cv2


@dataclass
class DataConfig:
    """Data loading and processing configuration."""
    
    # Patch extraction
    patch_size: int = 512
    stride: int = 256  # For sliding window extraction (if needed)
    min_positive_pixels: int = 100  # Minimum pixels per patch to include it
    max_patches_per_image: int = 200
    
    # Dataset
    num_workers: int = 0
    batch_size: int = 4
    shuffle: bool = False  # IterableDataset doesn't support shuffle
    
    # Caching
    use_image_cache: bool = True
    use_mask_cache: bool = True
    cache_size: int = 100


@dataclass
class ModelConfig:
    """Model architecture configuration."""
    
    # Encoder
    encoder_name: str = "efficientnet-b0"
    encoder_weights: str = "imagenet"
    encoder_freeze: bool = False  # Freeze encoder for transfer learning (disabled by default)
    
    # Architecture
    embedding_dim: int = 16
    decoder_channels: tuple = (16, 16, 16, 16, 16)
    decoder_attention_type: str = 'scse'
    
    # Input/Output
    in_channels: int = 3
    out_channels: int = 1


@dataclass
class LossConfig:
    """Loss function configuration for 8-component multi-task objective."""
    
    # === 8-Component Loss Weights (from improved-v1 research) ===
    alpha_seg: float = 2.0  # Weakly-supervised segmentation (critical main task)
    alpha_edge: float = 10.0  # Edge-aware loss (strong emphasis on boundaries)
    alpha_hv: float = 1.0  # HV regression (distance maps for shape)
    alpha_recon: float = 0.5  # Image reconstruction (regularization)
    alpha_obj_emb: float = 0.5  # Object-level embedding (hierarchical prototype)
    alpha_pixel_con: float = 0.1  # Pixel-level contrastive learning
    alpha_var: float = 0.1  # Total variation (smoothness regularization)
    alpha_small_hole: float = 0.1  # Small hole morphological loss
    
    # Segmentation loss params
    bce_dice_weight: float = 0.5
    lambda_bg_base: float = 0.05
    gt_weight: float = 1.0
    pseudo_pos_weight: float = 0.3
    pseudo_neg_weight: float = 0.3
    
    # Pseudo-labeling thresholds
    pos_thresh: float = 0.9
    neg_thresh: float = 0.2
    post_process_pseudo: bool = False
    min_size: int = 100
    min_hole_size: int = 100
    smooth_pseudo: bool = False
    smooth_radius: int = 1
    
    # Contrastive loss params
    temperature: float = 0.1
    max_samples: int = 512
    pseudo_neg_thresh: float = 0.1


@dataclass
class OptimizerConfig:
    """Optimizer and learning rate configuration."""
    
    # Optimizer
    optimizer_type: str = "NAdam"  # Options: "Adam", "NAdam", "SGD"
    learning_rate: float = 0.001
    weight_decay: float = 1e-2
    beta1: float = 0.9
    beta2: float = 0.999
    
    # Learning rate schedule
    use_scheduler: bool = False
    scheduler_type: str = "cosine"  # Options: "cosine", "step", "linear"
    warmup_epochs: int = 5
    total_epochs: int = 100
    
    # Gradient
    use_amp: bool = True  # Automatic Mixed Precision
    grad_clip: Optional[float] = 1.0 # Gradient clipping value (None to disable)


@dataclass
class AugmentationConfig:
    """Data augmentation configuration."""
    
    # Augmentation flags
    random_scale: bool = True
    scale_limit: float = -0.1
    scale_prob: float = 0.1
    
    vertical_flip: bool = True
    vertical_flip_prob: float = 0.5
    
    horizontal_flip: bool = True
    horizontal_flip_prob: float = 0.5
    
    blur: bool = False
    blur_prob: float = 0.5
    
    gauss_noise: bool = True
    gauss_noise_prob: float = 0.5
    gauss_var_limit: tuple = (10.0, 50.0)
    
    iso_noise: bool = True
    iso_noise_prob: float = 0.5
    iso_intensity_range: tuple = (0.1, 0.5)
    iso_color_shift: tuple = (0.01, 0.05)
    
    brightness_contrast: bool = True
    brightness_contrast_prob: float = 0.5
    brightness_limit: float = 0.2
    contrast_limit: float = 0.2
    
    random_gamma: bool = True
    random_gamma_prob: float = 0.5
    gamma_limit: tuple = (80, 120)
    
    hue_saturation: bool = True
    hue_saturation_prob: float = 0.9
    hue_shift_limit: int = 20
    sat_shift_limit: int = 10
    val_shift_limit: int = 10
    
    rotation: bool = True
    rotation_prob: float = 1.0


@dataclass
class TrainingConfig:
    """Training loop configuration."""
    
    # Epochs and iterations
    num_epochs: int = 100
    checkpoint_interval: int = 50
    log_interval: int = 10
    
    # Device
    device: str = "cuda"
    distributed: bool = False
    
    # Checkpointing
    save_checkpoint_interval: int = 50
    resume_from_checkpoint: Optional[str] = None
    best_model_metric: str = "loss"  # Options: "loss", "iou", "dice"


@dataclass
class DLConfig:
    """
    Master configuration class combining all sub-configurations.
    
    This is the main entry point for all configuration parameters.
    """
    
    # Sub-configurations
    data: DataConfig = None
    model: ModelConfig = None
    loss: LossConfig = None
    optimizer: OptimizerConfig = None
    augmentation: AugmentationConfig = None
    training: TrainingConfig = None
    
    # Ray/Distributed
    boost_count: int = 5
    batch_size_infer: int = 4
    
    def __post_init__(self):
        """Initialize default sub-configurations if not provided."""
        if self.data is None:
            self.data = DataConfig()
        if self.model is None:
            self.model = ModelConfig()
        if self.loss is None:
            self.loss = LossConfig()
        if self.optimizer is None:
            self.optimizer = OptimizerConfig()
        if self.augmentation is None:
            self.augmentation = AugmentationConfig()
        if self.training is None:
            self.training = TrainingConfig()


def get_default_config() -> DLConfig:
    """Get default configuration."""
    return DLConfig()


def get_augmentation_transforms(patch_size: int, config: Optional[AugmentationConfig] = None) -> A.Compose:
    """
    Build augmentation pipeline from configuration.
    
    Args:
        patch_size: Size of patches to augment.
        config: AugmentationConfig object. Uses defaults if None.
    
    Returns:
        Albumentations Compose object.
    """
    if config is None:
        config = AugmentationConfig()
    
    transforms = []
    
    # Random scale
    if config.random_scale:
        transforms.append(
            A.RandomScale(scale_limit=config.scale_limit, p=config.scale_prob)
        )
    
    # Pad if needed
    transforms.append(A.PadIfNeeded(min_height=patch_size, min_width=patch_size))
    
    # Flips
    if config.vertical_flip:
        transforms.append(A.VerticalFlip(p=config.vertical_flip_prob))
    
    if config.horizontal_flip:
        transforms.append(A.HorizontalFlip(p=config.horizontal_flip_prob))
    
    # Blur
    if config.blur:
        transforms.append(A.Blur(p=config.blur_prob))
    
    # Noise
    if config.gauss_noise:
        transforms.append(
            A.GaussNoise(p=config.gauss_noise_prob, var_limit=config.gauss_var_limit)
        )
    
    if config.iso_noise:
        transforms.append(
            A.ISONoise(
                p=config.iso_noise_prob,
                intensity=config.iso_intensity_range,
                color_shift=config.iso_color_shift
            )
        )
    
    # Brightness/Contrast
    if config.brightness_contrast:
        transforms.append(
            A.RandomBrightnessContrast(
                p=config.brightness_contrast_prob,
                brightness_limit=(-config.brightness_limit, config.brightness_limit),
                contrast_limit=(-config.contrast_limit, config.contrast_limit),
                brightness_by_max=True
            )
        )
    
    # Gamma
    if config.random_gamma:
        transforms.append(
            A.RandomGamma(p=config.random_gamma_prob, gamma_limit=config.gamma_limit, eps=1e-7)
        )
    
    # Hue/Saturation
    if config.hue_saturation:
        transforms.append(
            A.HueSaturationValue(
                hue_shift_limit=config.hue_shift_limit,
                sat_shift_limit=config.sat_shift_limit,
                val_shift_limit=config.val_shift_limit,
                p=config.hue_saturation_prob
            )
        )
    
    # Rotation
    if config.rotation:
        transforms.append(
            A.Rotate(p=config.rotation_prob, border_mode=cv2.BORDER_REFLECT)
        )
    
    # Random crop
    transforms.append(A.RandomCrop(patch_size, patch_size))
    
    # To tensor
    transforms.append(ToTensorV2())
    
    return A.Compose(transforms)
