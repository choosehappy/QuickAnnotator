"""
Loss functions for multi-task weakly supervised segmentation.

This module contains various loss functions used in the training pipeline,
including segmentation losses, contrastive losses, and regularization terms.
"""

from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import segmentation_models_pytorch as smp
from skimage.morphology import disk, opening, closing, remove_small_objects, remove_small_holes


def compute_sobel_edge_mask(mask: torch.Tensor) -> torch.Tensor:
    """
    Compute edge mask using Sobel operator.

    Args:
        mask: Input mask of shape (B, 1, H, W).

    Returns:
        Edge mask of shape (B, 1, H, W).
    """
    weight_x = torch.tensor([[[[-1, 0, 1],
                               [-2, 0, 2],
                               [-1, 0, 1]]]], device=mask.device, dtype=torch.float32)
    weight_y = torch.tensor([[[[-1, -2, -1],
                               [0, 0, 0],
                               [1, 2, 1]]]], device=mask.device, dtype=torch.float32)

    Gx = F.conv2d(mask.float(), weight_x, padding=1)
    Gy = F.conv2d(mask.float(), weight_y, padding=1)

    edge = torch.sqrt(Gx**2 + Gy**2)
    edge_mask = (edge > 0).float()
    return edge_mask


def edge_loss(positive_mask: torch.Tensor, pred: torch.Tensor) -> torch.Tensor:
    """
    Compute edge-aware loss using Sobel edges.

    Args:
        positive_mask: Ground truth mask of shape (B, 1, H, W).
        pred: Predictions of shape (B, 1, H, W).

    Returns:
        Edge loss value.
    """
    edge_mask = compute_sobel_edge_mask(positive_mask)
    bce_edge = nn.BCEWithLogitsLoss(reduction='none')(pred, positive_mask)
    bce_edge = (bce_edge * edge_mask).sum() / (edge_mask.sum() + 1e-6)
    return bce_edge


def masked_mse_loss(preds: torch.Tensor, targets: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """
    Compute masked MSE loss.

    Args:
        preds: Predictions.
        targets: Targets.
        mask: Mask to apply.

    Returns:
        Masked MSE loss.
    """
    criterion = nn.MSELoss(reduction='none')
    per_element_loss = criterion(preds, targets)

    # Expand mask to match channel dimension if needed
    if mask.dim() < per_element_loss.dim():
        mask = mask.unsqueeze(1)  # [B,1,H,W]

    # Apply mask
    masked_loss = per_element_loss * mask

    # Average over valid pixels, avoid division by zero
    return masked_loss.sum() / mask.sum().clamp(min=1)


def hierarchical_prototype_loss(
    obj_embeddings: torch.Tensor,
    positive_mask: torch.Tensor,
    lambda_img: float = 1.0,
    lambda_batch: float = 0.5,
    eps: float = 1e-6,
) -> torch.Tensor:
    """
    Compute hierarchical prototype loss for object embeddings.

    Encourages embeddings of positive pixels to cluster around a prototype,
    computed per-image and across the batch.

    Args:
        obj_embeddings: Object embeddings of shape (B, D, H, W).
        positive_mask: Positive mask of shape (B, 1, H_orig, W_orig).
        lambda_img: Weight for per-image loss.
        lambda_batch: Weight for batch-global loss.
        eps: Small value for numerical stability.

    Returns:
        Combined prototype loss.
    """
    B, D, H, W = obj_embeddings.shape
    device = obj_embeddings.device

    # Resize mask ONCE
    mask = F.interpolate(
        positive_mask.float(),
        size=(H, W),
        mode='nearest'
    )[:, 0]  # (B, H, W)

    # Reorder embeddings once
    emb = obj_embeddings.permute(0, 2, 3, 1)  # (B, H, W, D)

    # --------
    # Batch-global loss (fully vectorized)
    # --------
    pos_all = mask > 0
    if pos_all.sum() >= 2:
        emb_all = emb[pos_all]  # (N_all, D)
        proto_all = emb_all.mean(dim=0, keepdim=True)
        batch_loss = ((emb_all - proto_all) ** 2).sum(dim=1).mean()
    else:
        batch_loss = torch.zeros((), device=device)

    # --------
    # Per-image loss (cheap loop over B)
    # --------
    img_loss = torch.zeros((), device=device)
    valid_imgs = 0

    for b in range(B):
        pos = mask[b] > 0
        if pos.sum() < 2:
            continue

        emb_b = emb[b][pos]  # (N_b, D)
        proto_b = emb_b.mean(dim=0, keepdim=True)
        img_loss = img_loss + ((emb_b - proto_b) ** 2).sum(dim=1).mean()
        valid_imgs += 1

    if valid_imgs > 0:
        img_loss = img_loss / valid_imgs

    return lambda_img * img_loss + lambda_batch * batch_loss


def total_variation_loss(mask: torch.Tensor) -> torch.Tensor:
    """
    Compute total variation loss for smoothness.

    Args:
        mask: Input mask of shape (B, 1, H, W).

    Returns:
        Total variation loss.
    """
    dx = torch.abs(mask[:, :, 1:, :] - mask[:, :, :-1, :])
    dy = torch.abs(mask[:, :, :, 1:] - mask[:, :, :, :-1])
    return (dx.mean() + dy.mean())


def local_density(mask: torch.Tensor, kernel_size: int = 3) -> torch.Tensor:
    """
    Compute local density using average pooling.

    Args:
        mask: Input mask of shape (B, 1, H, W).
        kernel_size: Size of the pooling kernel.

    Returns:
        Local density map.
    """
    density = F.avg_pool2d(mask, kernel_size=kernel_size, stride=1, padding=kernel_size//2)
    return density


def small_hole_loss(pred_mask_probs: torch.Tensor, kernel_size: int = 3) -> torch.Tensor:
    """
    Compute loss to encourage filling small holes.

    Args:
        pred_mask_probs: Predicted probabilities of shape (B, 1, H, W).
        kernel_size: Kernel size for density computation.

    Returns:
        Small hole loss.
    """
    # pred_mask_probs is already probabilities
    density = local_density(pred_mask_probs, kernel_size)
    loss = (pred_mask_probs * (1 - density) + (1 - pred_mask_probs) * density).mean()
    return loss


class WeaklySupervisedSegmentationLoss(nn.Module):
    """
    Weakly supervised segmentation loss with pseudo-labeling.

    Combines BCE, Dice, and background losses with dynamic weighting.
    Supports pseudo-positive and pseudo-negative generation.
    """

    def __init__(
        self,
        bce_dice_weight: float = 0.5,
        lambda_bg_base: float = 0.05,
        dice_smooth: float = 1.0,
        gt_weight: float = 1.0,
        pseudo_pos_weight: float = 0.3,
        pseudo_neg_weight: float = 0.3
    ):
        """
        Initialize the loss.

        Args:
            alpha: Weight for BCE vs Dice.
            lambda_bg_base: Base weight for background loss.
            dice_smooth: Smoothing for Dice loss.
            gt_weight: Weight for ground-truth positives.
            pseudo_pos_weight: Weight for pseudo-positives.
            pseudo_neg_weight: Weight for pseudo-negatives.
        """
        super().__init__()
        self.bce_dice_weight = bce_dice_weight
        self.lambda_bg_base = lambda_bg_base
        self.gt_weight = gt_weight
        self.pseudo_pos_weight = pseudo_pos_weight
        self.pseudo_neg_weight = pseudo_neg_weight

        self.dice_loss_fn = smp.losses.DiceLoss(
            mode='binary', from_logits=False, smooth=dice_smooth
        )
        self.bce_loss_fn = nn.BCEWithLogitsLoss(reduction='none')

    @torch.no_grad()
    def generate_pseudo_labels(
        self,
        pred_probs: torch.Tensor,
        positive_mask: torch.Tensor,
        threshold_pos: float = 0.9,
        threshold_neg: float = 0.2,
        post_process: bool = False,
        min_size: int = 100,
        min_hole_size: int = 100,
        smooth: bool = False,
        smooth_radius: int = 1
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Generate pseudo-positive and pseudo-negative masks.

        Args:
            pred_probs: Predicted probabilities of shape (B, 1, H, W).
            positive_mask: Known positive mask of shape (B, 1, H, W).
            threshold_pos: Threshold for pseudo-positives.
            threshold_neg: Threshold for pseudo-negatives.
            post_process: Whether to apply morphological post-processing.
            min_size: Minimum size for objects.
            min_hole_size: Minimum size for holes.
            smooth: Whether to smooth edges.
            smooth_radius: Radius for smoothing.

        Returns:
            Tuple of pseudo_pos and pseudo_neg masks.
        """
        device = pred_probs.device
        unknown_mask = 1 - positive_mask

        # pred_probs is already probabilities

        # Initial pseudo-labels
        pseudo_pos = ((pred_probs > threshold_pos) & (unknown_mask > 0)).float()
        pseudo_neg = ((pred_probs < threshold_neg) & (unknown_mask > 0)).float()

        if post_process:
            batch_size = pred_probs.shape[0]
            struct = disk(smooth_radius)  # Structuring element for smoothing

            for mask in [pseudo_pos, pseudo_neg]:
                mask_np = mask.cpu().numpy().astype(bool)

                for i in range(batch_size):
                    m = mask_np[i, 0]
                    # Remove small objects
                    m = remove_small_objects(m, max_size=min_size)
                    # Fill small holes
                    m = remove_small_holes(m, max_size=min_hole_size)
                    # Optional smoothing
                    if smooth:
                        m = opening(m, struct)
                        m = closing(m, struct)
                    mask_np[i] = m
                mask.copy_(torch.from_numpy(mask_np.astype(float)).to(device))

        return pseudo_pos, pseudo_neg

    def forward(
        self,
        pred: torch.Tensor,
        positive_mask: torch.Tensor,
        pseudo_pos: Optional[torch.Tensor] = None,
        pseudo_neg: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Compute the loss.

        Args:
            pred: Predictions of shape (B, 1, H, W).
            positive_mask: Ground-truth positive mask of shape (B, 1, H, W).
            pseudo_pos: Pseudo-positive mask.
            pseudo_neg: Pseudo-negative mask.

        Returns:
            Combined loss value.
        """
        eps = 1e-6
        B, _, H, W = pred.shape

        # Assign weights per pixel
        weight_map = torch.zeros_like(pred)

        # GT positives
        weight_map = weight_map + positive_mask * self.gt_weight

        # Pseudo positives
        if pseudo_pos is not None:
            weight_map = weight_map + pseudo_pos * self.pseudo_pos_weight

        # Pseudo negatives
        if pseudo_neg is not None:
            weight_map = weight_map + pseudo_neg * self.pseudo_neg_weight

        # Combined positive mask for Dice and BCE
        combined_pos = torch.clamp(positive_mask + (pseudo_pos if pseudo_pos is not None else 0), 0, 1)

        # Positive BCE
        bce_pos = self.bce_loss_fn(pred, combined_pos)
        bce_pos = (bce_pos * weight_map).sum() / (weight_map.sum() + eps)

        # Dice on positives (weighted by GT + pseudo_pos)
        dice = self.dice_loss_fn(pred * combined_pos, combined_pos.float())

        # Dynamic lambda_bg
        tile_pos_frac = combined_pos.view(B, -1).mean(dim=1)
        lambda_bg = self.lambda_bg_base * (1 - tile_pos_frac)
        lambda_bg = lambda_bg.view(B, 1, 1, 1)

        # BCE on unknown pixels + pseudo-negatives
        unknown_mask = 1 - combined_pos
        unknown_weight = lambda_bg
        if pseudo_neg is not None:
            unknown_mask2 = torch.clamp(unknown_mask + pseudo_neg, 0, 1)
        else:
            unknown_mask2 = unknown_mask
        bce_bg = self.bce_loss_fn(pred, torch.zeros_like(pred))
        bce_bg = (bce_bg * unknown_mask2 * unknown_weight).sum() / (unknown_mask2.sum() + eps)
        
        loss = self.bce_dice_weight * bce_pos + (1 - self.bce_dice_weight) * dice + bce_bg.mean()
        return loss


class HierarchicalPixelContrastiveLoss(nn.Module):
    """
    Hierarchical pixel-level contrastive loss.

    Encourages positive pixels to have similar embeddings and dissimilar to negatives.
    """

    def __init__(self, temperature: float = 0.1, max_samples: int = 512, pseudo_neg_thresh: float = 0.1):
        """
        Initialize the loss.

        Args:
            temperature: Temperature for softmax.
            max_samples: Maximum samples for positives/negatives.
            pseudo_neg_thresh: Threshold for pseudo-negatives.
        """
        super().__init__()
        self.temperature = temperature
        self.max_samples = max_samples
        self.pseudo_neg_thresh = pseudo_neg_thresh

    def forward(
        self,
        pixel_embeddings: torch.Tensor,
        positive_mask: torch.Tensor,
        pred_probs: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Compute contrastive loss.

        Args:
            pixel_embeddings: Embeddings of shape (B, D, H, W).
            positive_mask: Positive mask of shape (B, 1, H_orig, W_orig).
            pred_probs: Predicted probabilities for pseudo-negatives of shape (B, 1, H_orig, W_orig).

        Returns:
            Contrastive loss.
        """
        B, D, H, W = pixel_embeddings.shape
        device = pixel_embeddings.device
        loss_total = torch.zeros((), device=device)
        valid = 0

        # Resize positive mask to match embedding resolution
        mask_resized = F.interpolate(
            positive_mask.float(),
            size=(H, W),
            mode='nearest'
        )[:, 0]  # (B, H, W)

        # Resize predictions if provided
        if pred_probs is not None:
            # pred_probs is already probabilities
            pred_resized = F.interpolate(
                pred_probs.float(),
                size=(H, W),
                mode='bilinear',
                align_corners=False
            )[:, 0]  # (B, H, W)

        for b in range(B):
            # Flatten and normalize embeddings
            emb = pixel_embeddings[b].permute(1, 2, 0).reshape(-1, D)

            # Positive indices
            pos_mask = mask_resized[b] > 0
            pos_idx = pos_mask.view(-1).nonzero(as_tuple=True)[0]
            if pos_idx.numel() < 2:
                continue
            if pos_idx.numel() > self.max_samples:
                pos_idx = pos_idx[torch.randperm(pos_idx.numel(), device=device)[:self.max_samples]]
            z_pos = emb[pos_idx]

            # All-to-all positive similarity
            sim_pos = z_pos @ z_pos.T / self.temperature
            mask_eye = torch.eye(len(z_pos), device=device).bool()
            sim_pos.masked_fill_(mask_eye, -float('inf'))  # Remove self-similarity
            numerator = sim_pos.exp().sum(dim=1)

            # Denominator includes positives
            denom = numerator.clone()

            # Pseudo-negatives
            if pred_probs is not None:
                pred_flat = pred_resized[b].view(-1)
                neg_mask = (pred_flat < self.pseudo_neg_thresh) & (~pos_mask.view(-1))
                neg_idx = neg_mask.nonzero(as_tuple=True)[0]
                if neg_idx.numel() > 0:
                    if neg_idx.numel() > self.max_samples:
                        neg_idx = neg_idx[torch.randperm(neg_idx.numel(), device=device)[:self.max_samples]]
                    z_neg = emb[neg_idx]
                    sim_neg = z_pos @ z_neg.T / self.temperature
                    denom += sim_neg.exp().sum(dim=1)

            # Loss
            loss = -torch.log(numerator / (denom + 1e-8))
            loss_total += loss.mean()
            valid += 1

        return loss_total / max(valid, 1)