"""
Training script for multi-task weakly supervised segmentation.

This script trains the MultiTaskSegmentationModel using various auxiliary losses
on patched datasets with augmentations.
"""

import argparse
from dataclasses import dataclass
import glob
from pathlib import Path
from typing import Optional

import albumentations as A
from albumentations.pytorch import ToTensorV2
import cv2
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

from datasets import PatchedSegmentationDataset
from losses import (
    WeaklySupervisedSegmentationLoss,
    HierarchicalPixelContrastiveLoss,
    masked_mse_loss,
    edge_loss,
    hierarchical_prototype_loss,
    total_variation_loss,
    small_hole_loss
)
from models import MultiTaskSegmentationModel


@dataclass
class Config:
    """Configuration for training."""
    data_dir: Path = Path("./images")
    log_dir: str = "runs/experiment1"
    num_epochs: int = 100
    batch_size: int = 4
    lr: float = 1e-3
    weight_decay: float = 1e-5
    patch_size: int = 512
    stride: int = 256
    min_positive_pixels: int = 1000
    max_patches_per_image: int = 200
    num_workers: int = 8
    log_interval: int = 10

    # Model args
    encoder_name: str = "efficientnet-b0"
    embedding_dim: int = 16

    # Pseudo-labeling params
    min_size: int = 100
    min_hole_size: int = 100
    post_process: bool = True
    smooth: bool = False
    smooth_radius: int = 2

    # Loss weights
    alpha_seg: float = 2.0
    alpha_hv: float = 1.0
    alpha_edge: float = 10.0
    alpha_recon: float = 0.5
    alpha_obj_emb: float = 0.5
    alpha_pixel_con: float = 0.1
    alpha_var: float = 0.1
    alpha_small_hole: float = 0.1

    # Loss params
    bce_dice_weight: float = 0.5
    lambda_bg_base: float = 0.05
    gt_weight: float = 1.0
    pseudo_pos_weight: float = 0.3
    pseudo_neg_weight: float = 0.3
    pos_thresh: float = 0.8
    temperature: float = 0.1
    max_samples: int = 512
    pseudo_neg_thresh: float = 0.1


def get_transforms(patch_size: int) -> A.Compose:
    """
    Get data augmentation transforms.

    Args:
        patch_size: Size of the patches.

    Returns:
        Albumentations compose object.
    """
    transforms = A.Compose([
        A.RandomScale(scale_limit=-0.1, p=0.1),
        A.PadIfNeeded(min_height=patch_size, min_width=patch_size),
        A.VerticalFlip(p=0.5),
        A.HorizontalFlip(p=0.5),
        # A.Blur(p=.5),
        # A.Downscale(p=.25, scale_min=0.64, scale_max=0.99),
        A.GaussNoise(p=0.5, var_limit=(10.0, 50.0)),
        # A.GridDistortion(p=.5, num_steps=5, distort_limit=(-0.3, 0.3),
        #                   border_mode=cv2.BORDER_REFLECT),
        A.ISONoise(p=0.5, intensity=(0.1, 0.5), color_shift=(0.01, 0.05)),
        A.RandomBrightnessContrast(
            p=0.5,
            brightness_limit=(-0.2, 0.2),
            contrast_limit=(-0.2, 0.2),
            brightness_by_max=True
        ),
        A.RandomGamma(p=0.5, gamma_limit=(80, 120), eps=1e-07),
        # A.MultiplicativeNoise(p=.5, multiplier=(0.9, 1.1), per_channel=True, elementwise=True),
        A.HueSaturationValue(
            hue_shift_limit=20,
            sat_shift_limit=10,
            val_shift_limit=10,
            p=0.9
        ),
        A.Rotate(p=1, border_mode=cv2.BORDER_REFLECT),
        A.RandomCrop(patch_size, patch_size),
        ToTensorV2()
    ])
    return transforms


def parse_args() -> Config:
    """Parse command-line arguments into Config."""
    parser = argparse.ArgumentParser(description="Train multi-task segmentation model")
    parser.add_argument("--data_dir", type=Path, default=Path("./images"), help="Data directory")
    parser.add_argument("--log_dir", type=str, default="runs/experiment1", help="TensorBoard log directory")
    parser.add_argument("--num_epochs", type=int, default=100, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--weight_decay", type=float, default=1e-5, help="Weight decay")
    parser.add_argument("--patch_size", type=int, default=512, help="Patch size")
    parser.add_argument("--stride", type=int, default=256, help="Patch stride")
    parser.add_argument("--min_positive_pixels", type=int, default=1000, help="Min positive pixels per patch")
    parser.add_argument("--max_patches_per_image", type=int, default=200, help="Max patches per image")
    parser.add_argument("--num_workers", type=int, default=8, help="DataLoader workers")
    parser.add_argument("--log_interval", type=int, default=10, help="Logging interval")

    # Model args
    parser.add_argument("--encoder_name", type=str, default="efficientnet-b0", help="Encoder name")
    parser.add_argument("--embedding_dim", type=int, default=16, help="Embedding dimension")

    # Loss weights
    parser.add_argument("--alpha_seg", type=float, default=2.0, help="Segmentation loss weight")
    parser.add_argument("--alpha_hv", type=float, default=1.0, help="HV loss weight")
    parser.add_argument("--alpha_edge", type=float, default=10.0, help="Edge loss weight")
    parser.add_argument("--alpha_recon", type=float, default=0.5, help="Reconstruction loss weight")
    parser.add_argument("--alpha_obj_emb", type=float, default=0.5, help="Object embedding loss weight")
    parser.add_argument("--alpha_pixel_con", type=float, default=0.1, help="Pixel contrastive loss weight")
    parser.add_argument("--alpha_var", type=float, default=0.1, help="Variation loss weight")
    parser.add_argument("--alpha_small_hole", type=float, default=0.1, help="Small hole loss weight")

    # Loss params
    parser.add_argument("--lambda_bg_base", type=float, default=0.05, help="Background loss base")
    parser.add_argument("--gt_weight", type=float, default=1.0, help="GT weight")
    parser.add_argument("--pseudo_pos_weight", type=float, default=0.3, help="Pseudo-pos weight")
    parser.add_argument("--pseudo_neg_weight", type=float, default=0.3, help="Pseudo-neg weight")
    parser.add_argument("--pos_thresh", type=float, default=0.8, help="Positive threshold")
    parser.add_argument("--temperature", type=float, default=0.1, help="Contrastive temperature")
    parser.add_argument("--max_samples", type=int, default=512, help="Max samples for contrastive")
    parser.add_argument("--pseudo_neg_thresh", type=float, default=0.1, help="Pseudo-neg threshold")

    args = parser.parse_args()
    return Config(**vars(args))


def in_notebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        else:
            return False  # Other type (e.g., IPython terminal)
    except NameError:
        return False      # Standard Python interpreter



# +
# if __name__ == "__main__":
#     #----
#     if in_notebook():
#         import sys
#         sys.argv = ['']  # override for notebook
        
#     config = parse_args()
#     main(config)

# +
#------------------------
if in_notebook():
    import sys
    sys.argv = ['']  # override for notebook
    
config = parse_args()

# -

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Model
model = MultiTaskSegmentationModel(
    encoder_name=config.encoder_name,
    embedding_dim=config.embedding_dim
).to(device)

# Losses
seg_loss_fn = WeaklySupervisedSegmentationLoss(
    bce_dice_weight=config.bce_dice_weight,
    lambda_bg_base=config.lambda_bg_base,
    gt_weight=config.gt_weight,
    pseudo_pos_weight=config.pseudo_pos_weight,
    pseudo_neg_weight=config.pseudo_neg_weight
)

# +
pixel_contrastive_loss = HierarchicalPixelContrastiveLoss(
    temperature=config.temperature,
    max_samples=config.max_samples,
    pseudo_neg_thresh=config.pseudo_neg_thresh
)

mse_loss = nn.MSELoss()
# -

# Optimizer
optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=config.lr,
    weight_decay=config.weight_decay
)

# +
# Dataset
img_paths = sorted(glob.glob(str(config.data_dir / "*_img.png")))
mask_paths = sorted(glob.glob(str(config.data_dir / "*_mask.png")))

transforms = get_transforms(config.patch_size)
dataset = PatchedSegmentationDataset(
    img_paths=img_paths,
    mask_paths=mask_paths,
    patch_size=config.patch_size,
    stride=config.stride,
    min_positive_pixels=config.min_positive_pixels,
    max_patches_per_image=config.max_patches_per_image,
    shuffle_patches=True,
    transforms=transforms
)
# -

loader = DataLoader(
    dataset,
    batch_size=config.batch_size,
    num_workers=config.num_workers,
    shuffle=False,
    pin_memory=True
)

# TensorBoard
writer = SummaryWriter(log_dir=config.log_dir)

# +
# Training loop
total_step = 0
model.train()
for step in tqdm(range(config.num_epochs)):
    for batch_idx, (images, masks, hvs) in enumerate(loader):
        images = images.float().to(device) / 255.0
        masks = masks.float().to(device) / 255.0
        hvs = hvs.float().to(device)

        #with torch.amp.autocast('cuda', enabled=torch.cuda.is_available()):
        with torch.amp.autocast('cuda', enabled=False):
            outputs = model(
                images,
                return_recon=True,
                return_hv=True,
                return_obj_emb=True,
                return_pixel_emb=True
            )
            preds = outputs["preds"]
            hvs_outs = outputs["hv_map"]
            recon_images = outputs['recon']
            obj_emb = outputs['obj_emb']
            pixel_emb = outputs['pixel_emb']

            # Compute probabilities once for efficiency
            preds_prob = torch.sigmoid(preds)

            # Individual losses
            recon_loss = mse_loss(recon_images, images)
            obj_emb_loss = hierarchical_prototype_loss(obj_emb, masks)
            hv_loss = masked_mse_loss(hvs_outs, hvs, masks)
            edge_loss_val = edge_loss(masks, preds)

            # Pseudo-labels
            pseudo_pos, pseudo_neg = seg_loss_fn.generate_pseudo_labels(
                preds_prob, masks,
                threshold_pos=config.pos_thresh,
                post_process=config.post_process,
                min_size=config.min_size,
                min_hole_size=config.min_hole_size,
                smooth=config.smooth,
                smooth_radius=config.smooth_radius
            )
            seg_loss = seg_loss_fn(preds, masks, pseudo_pos=pseudo_pos, pseudo_neg=pseudo_neg)
            assert seg_loss> 0, "Seg loss negative!"


            pixel_con_loss = pixel_contrastive_loss(
                pixel_embeddings=pixel_emb,
                positive_mask=masks,
                pred_probs=preds_prob
            )

            var_loss = total_variation_loss(preds)
            small_hole_loss_val = small_hole_loss(preds_prob)

            # Total loss
            loss = (
                config.alpha_seg * seg_loss +
                config.alpha_hv * hv_loss +
                config.alpha_edge * edge_loss_val +
                config.alpha_recon * recon_loss +
                config.alpha_obj_emb * obj_emb_loss +
                config.alpha_pixel_con * pixel_con_loss +
                config.alpha_var * var_loss +
                config.alpha_small_hole * small_hole_loss_val
            )


            assert not torch.isnan(loss).item(), "Loss is NaN! Stopping execution."

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_step += 1

        # Logging
        if total_step % config.log_interval == 0:
            with torch.no_grad():
                writer.add_scalar("Loss/total", loss.item(), total_step)
                writer.add_scalar("Loss/segmentation", seg_loss.item(), total_step)
                writer.add_scalar("Loss/edge", edge_loss_val.item(), total_step)
                writer.add_scalar("Loss/hv", hv_loss.item(), total_step)
                writer.add_scalar("Loss/recon", recon_loss.item(), total_step)
                writer.add_scalar("Loss/obj_emb", obj_emb_loss.item(), total_step)
                writer.add_scalar("Loss/pixel_con", pixel_con_loss.item(), total_step)
                writer.add_scalar("Loss/var", var_loss.item(), total_step)
                writer.add_scalar("Loss/small_hole", small_hole_loss_val.item(), total_step)

                pred_mask = (preds > 0.5).float()
                accuracy = (pred_mask == masks).float().mean()
                writer.add_scalar("Metrics/accuracy", accuracy.item(), total_step)

                if hvs_outs is not None:
                    writer.add_scalar("HV/mean", hvs_outs.mean().item(), total_step)
                    writer.add_scalar("HV/max", hvs_outs.max().item(), total_step)
                    writer.add_scalar("HV/min", hvs_outs.min().item(), total_step)

                # Images (slow, so less frequent)
                if total_step % (config.log_interval * 10) == 0:
                    writer.add_image("imgs/img", images[0], total_step)
                    if recon_images is not None:
                        writer.add_image("imgs/recon", recon_images[0], total_step)
                    writer.add_image("imgs/preds", preds[0], total_step)
                    writer.add_image("imgs/preds_thresh", (preds[0] >= config.pos_thresh).float(), total_step)
                    writer.add_image("imgs/masks", masks[0], total_step)
                    if hvs_outs is not None:
                        writer.add_image("imgs/hv_map", hvs_outs[0], total_step)

        

writer.close()
# -

seg_loss

config.log_interval

seg_loss

seg_loss_fn(preds, masks, pseudo_pos=pseudo_pos, pseudo_neg=pseudo_neg)


    loss = self.alpha * bce_pos + (1 - self.alpha) * dice + bce_bg.mean()

# +

config.alpha_seg *.9 + (1-config.alpha_seg)*2.6+0.03
# -


