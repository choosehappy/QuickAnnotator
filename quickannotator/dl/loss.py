"""
Loss functions for multi-task weakly supervised segmentation.

This module contains various loss functions used in the training pipeline,
including segmentation losses, HV regression losses, and regularization terms.
"""

from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import segmentation_models_pytorch as smp

import cupy as cp
from cucim.skimage.morphology import (
    remove_small_objects, remove_small_holes, disk, opening, closing
)

import logging
logger = logging.getLogger(__name__)

def safe_loss(loss, name):
    if not torch.is_tensor(loss):
        loss = torch.tensor(loss, dtype=torch.float32)

    if torch.isnan(loss).any() or torch.isinf(loss).any():
        logger.error(f"[NaN/Inf detected] Loss '{name}' is invalid. Setting to zero.")
        return torch.zeros(1, device=loss.device, dtype=loss.dtype, requires_grad=True).squeeze()
    return loss


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


def edge_loss(positive_mask: torch.Tensor, pred: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
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
    bce_edge = (bce_edge * edge_mask).sum() / edge_mask.sum().clamp(min=1.0)
    return bce_edge, edge_mask


def interior_fill_loss_with_pseudo(
    pred_probs: torch.Tensor,
    edge_mask_gt: torch.Tensor,
    positive_mask: torch.Tensor,
    pseudo_positive_mask: torch.Tensor = None,
    dilate_kernel: int = 3,
    pseudo_weight: float = 0.2
) -> torch.Tensor:
    """
    Interior fill loss: encourages the interior of objects to be positive
    wherever edges exist, using GT + optional pseudo-positive regions.

    Args:
        pred_probs: Sigmoid predictions of shape (B,1,H,W), values in [0,1]
        positive_mask: GT mask, shape (B,1,H,W), values in {0,1}
        pseudo_positive_mask: Optional pseudo-positive mask, same shape, {0,1}
        dilate_kernel: Kernel size for dilating edges inward
        pseudo_weight: Weight for pseudo-positive regions relative to GT

    Returns:
        Scalar loss
    """
    
    # Step 2: Combine GT + pseudo positives
    if pseudo_positive_mask is not None:
        effective_mask = positive_mask.float() + pseudo_weight * pseudo_positive_mask.float()
        effective_mask = effective_mask.clamp(0, 1)
    else:
        effective_mask = positive_mask.float()

    # Step 3: Dilate edge inward to create interior band
    padding = dilate_kernel // 2
    dilated_edge = F.max_pool2d(edge_mask_gt, kernel_size=dilate_kernel, stride=1, padding=padding)

    # Step 4: Mask the dilated edge with effective positive regions
    interior_band = dilated_edge * effective_mask  # only penalize pixels inside positive regions

    # Step 5: Penalize low predicted probabilities inside interior_band
    loss = (interior_band * (1 - pred_probs)).sum() / (interior_band.sum().clamp(min=1.0))

    return loss


def total_variation_loss(mask: torch.Tensor) -> torch.Tensor:
    """
    Compute total variation loss for smoothness.

    Args:
        mask: Input mask of shape (B, 1, H, W).

    Returns:
        Total variation loss.
    """
    dx = torch.abs(mask[:, :, 1:, :] - mask[:, :, :-1, :]) ** 2
    dy = torch.abs(mask[:, :, :, 1:] - mask[:, :, :, :-1]) ** 2
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


class HVRegressionLoss(nn.Module):
    """
    Hypervector (HV) regression loss for predicting distance maps.
    
    Encourages the model to predict HV maps that match the ground truth HV maps
    computed from the segmentation masks.
    """
    
    def __init__(self, reduction: str = 'mean'):
        """
        Initialize HV regression loss.
        
        Args:
            reduction: How to reduce the loss ('mean', 'sum', or 'none').
        """
        super().__init__()
        self.reduction = reduction
        self.mse_loss = nn.MSELoss(reduction=reduction)
    
    def forward(
        self,
        pred_hv: torch.Tensor,
        target_hv: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Compute HV regression loss with optional masking, normalized per sample.

        Args:
            pred_hv: Predicted HV maps of shape (B, 1, H, W).
            target_hv: Target HV maps of shape (B, 1, H, W).
            mask: Optional mask (B, 1, H, W). Only compute loss on masked regions.

        Returns:
            HV regression loss (scalar).
        """
        if mask is not None:
            B = pred_hv.shape[0]

            # Flatten per sample
            diff_flat = (pred_hv - target_hv).view(B, -1)
            mask_flat = mask.view(B, -1)

            # Zero out diff outside mask BEFORE squaring to avoid inf * 0 = nan
            diff_masked = diff_flat * mask_flat

            num = (diff_masked ** 2).sum(dim=1)
            den = mask_flat.sum(dim=1).clamp(min=1.0)  # avoid division by tiny numbers

            mse_per_sample = num / den

            # Average over batch
            return mse_per_sample.mean()
        else:
            # Standard MSE loss
            return self.mse_loss(pred_hv, target_hv)



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
            bce_dice_weight: Weight for BCE vs Dice.
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
            mode='binary', from_logits=True, smooth=dice_smooth, ignore_index=-1  #AJ: added from_logits=True since our model outputs logits for segmentation head
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
        max_size: int = 100,
        max_hole_size: int = 100,
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
            max_size: Minimum size for objects.
            max_hole_size: Minimum size for holes.
            smooth: Whether to smooth edges.
            smooth_radius: Radius for smoothing.

        Returns:
            Tuple of pseudo_pos and pseudo_neg masks.
        """
        device = pred_probs.device
        unknown_mask = 1 - positive_mask

        # Initial pseudo-labels
        pseudo_pos = ((pred_probs >= threshold_pos) & (unknown_mask > 0)).float()
        pseudo_neg = ((pred_probs < threshold_neg) & (unknown_mask > 0)).float()

        if post_process:
            batch_size = pred_probs.shape[0]
            struct = disk(smooth_radius)  # cuCIM disk, returns cupy array

            for mask in [pseudo_pos, pseudo_neg]:
                # Convert entire batch to cupy bool — stays on GPU
                
                with cp.cuda.Device(mask.device.index):
                    cp.cuda.runtime.setDevice(mask.device.index)
                    torch.cuda.set_device(mask.device.index)
                    mask_cp = cp.from_dlpack(mask.bool().detach())  # zero-copy if possible

                for i in range(batch_size):
                    m = mask_cp[i, 0]
                    m = remove_small_objects(m, min_size=max_size)
                    m = remove_small_holes(m, area_threshold=max_hole_size)
                    if smooth:
                        m = opening(m, struct)
                        m = closing(m, struct)
                    mask_cp[i, 0] = m

                # Copy result back into the original torch tensor in-place
                mask.copy_(torch.from_dlpack(mask_cp.astype(cp.float32)))

        return pseudo_pos, pseudo_neg

    def forward(
        self,
        pred: torch.Tensor,
        positive_mask: torch.Tensor,
        pseudo_pos: Optional[torch.Tensor] = None,
        pseudo_neg: Optional[torch.Tensor] = None
    ) -> dict:
        """
        Compute the loss.

        Args:
            pred: Predictions of shape (B, 1, H, W).
            positive_mask: Ground-truth positive mask of shape (B, 1, H, W).
            pseudo_pos: Pseudo-positive mask.
            pseudo_neg: Pseudo-negative mask.

        Returns:
            Dictionary with individual loss components and combined loss.
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
        bce_pos_loss = (bce_pos * weight_map).sum() / (weight_map.sum() + eps)

        # Dice on positives 
        dice_mask = torch.full_like(combined_pos.float(), fill_value=-1)  # Initialize with ignore_index
        dice_mask[combined_pos == 1] = 1  # GT + pseudo_pos are positives
        if pseudo_neg is not None:
            dice_mask[pseudo_neg == 1] = 0   
        dice_loss = self.dice_loss_fn(pred, dice_mask) #TODO: consider per pixel dice weight - but would require custom functionality


        # --- unknown background --- > push to zero
        # Dynamic lambda_bg
        tile_pos_frac = combined_pos.view(B, -1).mean(dim=1)
        lambda_bg = self.lambda_bg_base * (1 + tile_pos_frac.clamp(max=.5)) #note: the more positive pixels, the stronger this should be to encourage better edges
        
        # ---- Build truly unknown mask ----
        truly_unknown = (combined_pos == 0)
        if pseudo_neg is not None:
            truly_unknown = truly_unknown & (pseudo_neg == 0)

        truly_unknown = truly_unknown.float()

        # ---- BCE toward zero ----
        bce_bg = self.bce_loss_fn(pred, torch.zeros_like(pred))

        # Flatten per sample
        bce_bg_flat = (bce_bg * truly_unknown).view(B, -1)
        mask_flat = truly_unknown.view(B, -1)

        # Per-sample numerator and denominator
        num = bce_bg_flat.sum(dim=1)                     # (B,)
        den = mask_flat.sum(dim=1)                       # (B,)

        # Avoid division when no unknown pixels exist
        loss_per_sample = torch.zeros_like(num)
        valid = den > 0
        loss_per_sample[valid] = num[valid] / (den[valid] + eps)

        # Apply per-sample lambda_bg 
        bce_bg_loss = (lambda_bg * loss_per_sample).mean()

        # Combined loss
        combined_loss = self.bce_dice_weight * bce_pos_loss + (1 - self.bce_dice_weight) * dice_loss +  bce_bg_loss
        
        return {
            'bce_pos': bce_pos_loss,
            'dice': dice_loss,
            'bce_bg': bce_bg_loss,
            'total': combined_loss
        }


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


class MultiTaskLoss(nn.Module):
    """
    Comprehensive multi-task loss combining 9 auxiliary losses:
    1. Segmentation (weakly-supervised with pseudo-labels)
    2. Edge-aware segmentation
    3. HV regression (distance maps)
    4. Image reconstruction
    5. Object-level embedding (hierarchical prototype clustering)
    6. Pixel-level contrastive learning
    7. Total variation (smoothness regularization)
    8. Small hole morphological regularization
    9. Consitency loss between different views of the same image (e.g. different augmentations) - encourages stable predictions under transformations
    
    This is the core multi-task objective for the improved training paradigm.
    """
    
    def __init__(
        self,
        alpha_seg: float = 1.0,
        alpha_edge: float = 0.1,
        alpha_hv: float = 0.5,
        alpha_recon: float = 0.5,
        alpha_obj_emb: float = 0.1,
        alpha_pixel_con: float = 0.1,
        alpha_var: float = 0.01,
        alpha_small_hole: float = 0.01,
        alpha_interior: float = 0.05,
        alpha_consistency: float = 0.05,
        alpha_obj_view_cont: float = 0.05,
        bce_dice_weight: float = 0.5,
        temperature: float = 0.1,
        max_samples: int = 512,
        pos_thresh: float = 0.5,
        post_process_pseudo: bool = False,
        max_size: int = 100,
        max_hole_size: int = 100,
        smooth_pseudo: bool = False,
        smooth_radius: int = 1,
    ):
        """
        Initialize 8-component multi-task loss.
        
        Args:
            alpha_seg: Weight for weakly-supervised segmentation loss.
            alpha_edge: Weight for edge-aware loss.
            alpha_hv: Weight for HV regression loss.
            alpha_recon: Weight for reconstruction loss.
            alpha_obj_emb: Weight for object embedding loss.
            alpha_pixel_con: Weight for pixel contrastive loss.
            alpha_var: Weight for total variation loss.
            alpha_small_hole: Weight for small hole morphology loss.
            alpha_interior: Weight for interior fill loss.
            bce_dice_weight: Balance between BCE and Dice in segmentation.
            temperature: Temperature for contrastive similarity.
            max_samples: Max samples for contrastive learning.
            pos_thresh: Threshold for positive predictions.
            post_process_pseudo: Whether to post-process pseudo-labels with morphology.
            max_size: Minimum object size for morphological filtering.
            max_hole_size: Minimum hole size for morphological filtering.
            smooth_pseudo: Whether to smooth pseudo-labels.
            smooth_radius: Radius for smoothing structuring element.
        """
        super().__init__()
        self.alpha_seg = alpha_seg
        self.alpha_edge = alpha_edge
        self.alpha_hv = alpha_hv
        self.alpha_recon = alpha_recon
        self.alpha_obj_emb = alpha_obj_emb
        self.alpha_pixel_con = alpha_pixel_con
        self.alpha_var = alpha_var
        self.alpha_interior = alpha_interior
        self.alpha_small_hole = alpha_small_hole
        self.alpha_consistency = alpha_consistency
        self.alpha_obj_view_cont = alpha_obj_view_cont
        self.pos_thresh = pos_thresh
        self.post_process_pseudo = post_process_pseudo
        self.max_size = max_size
        self.max_hole_size = max_hole_size
        self.smooth_pseudo = smooth_pseudo
        self.smooth_radius = smooth_radius
        
        # Loss components
        self.seg_loss_fn = WeaklySupervisedSegmentationLoss(bce_dice_weight=bce_dice_weight)
        self.hv_loss_fn = HVRegressionLoss()
        self.contrastive_loss_fn = HierarchicalPixelContrastiveLoss(
            temperature=temperature,
            max_samples=max_samples
        )
        self.recon_loss_fn = nn.MSELoss()
    
    def forward(
        self,
        model_output: dict,
        positive_mask: torch.Tensor,
        target_hv: torch.Tensor,
        images: Optional[torch.Tensor] = None,
        pred_probs: Optional[torch.Tensor] = None,
    ) -> dict:
        """
        Compute all 8 multi-task losses.
        
        Args:
            model_output: Dictionary from UNetMultiTask model containing:
                - 'preds': Segmentation logits (B, 1, H, W)
                - 'hv_map': HV predictions if return_hv=True (B, 1, H, W)
                - 'recon': Reconstructed image if return_recon=True (B, 3, H, W)
                - 'obj_emb': Object embeddings if return_obj_emb=True (B, D, H, W)
                - 'pixel_emb': Pixel embeddings if return_pixel_emb=True (B, D, H, W)
            positive_mask: Ground truth mask (B, 1, H, W).
            target_hv: Target HV maps (B, 1, H, W).
            images: Original images for reconstruction loss (B, 3, H, W).
            pred_probs: Pre-computed prediction probabilities for efficiency (B, 1, H, W).
            
        Returns:
            Dictionary with 'total' loss and individual component losses for logging.
        """
        losses = {}
        
        # === LOSS 1: Segmentation (Weakly-Supervised) ===
        pred_seg = model_output['preds']
        if pred_probs is None:
            pred_probs = torch.sigmoid(pred_seg)
        
        # Generate pseudo-labels for weakly-supervised learning
        pseudo_pos, pseudo_neg = self.seg_loss_fn.generate_pseudo_labels(
            pred_probs, positive_mask,
            threshold_pos=self.pos_thresh,
            post_process=self.post_process_pseudo,
            max_size=self.max_size,
            max_hole_size=self.max_hole_size,
            smooth=self.smooth_pseudo,
            smooth_radius=self.smooth_radius
        )

        losses['img_pseudo_pos'] = pseudo_pos[0,::].detach()  # Keep on GPU, return as tensor
        losses['img_pseudo_neg'] = pseudo_neg[0,::].detach()  # Keep on GPU, return as tensor

        seg_loss_dict = self.seg_loss_fn(pred_seg, positive_mask, pseudo_pos=pseudo_pos, pseudo_neg=pseudo_neg)
        loss_seg = seg_loss_dict['total']
        losses['segmentation'] = safe_loss(loss_seg, 'segmentation')
        losses['seg_bce_pos'] = safe_loss(seg_loss_dict['bce_pos'], 'seg_bce_pos')
        losses['seg_dice'] = safe_loss(seg_loss_dict['dice'], 'seg_dice')
        losses['seg_bce_bg'] = safe_loss(seg_loss_dict['bce_bg'], 'seg_bce_bg')
        
        # === LOSS 2: Edge-Aware Loss ===
        loss_edge , edge_mask_gt = edge_loss(positive_mask, pred_seg)
        loss_edge = safe_loss(loss_edge, 'edge')
        losses['edge'] = loss_edge

        # === LOSS 2.1: Interior fill  Loss ===
        loss_interior = interior_fill_loss_with_pseudo(pred_probs, positive_mask, edge_mask_gt,
                                                       pseudo_positive_mask=pseudo_pos, dilate_kernel=3, pseudo_weight=0.2)
        loss_interior = safe_loss(loss_interior, 'interior_fill')
        losses['interior_fill'] = loss_interior


        # === LOSS 3: HV Regression Loss ===
        loss_hv = torch.tensor(0.0, device=pred_seg.device)
        if 'hv_map' in model_output and self.alpha_hv > 0:
            pred_hv = model_output['hv_map']
            loss_hv = (
                self.hv_loss_fn(pred_hv, target_hv, mask=positive_mask)
                + .1*self.hv_loss_fn(pred_hv, target_hv, mask=pseudo_pos)
            )
        loss_hv = safe_loss(loss_hv, 'hv')
        losses['hv'] = loss_hv
        
        # === LOSS 4: Image Reconstruction Loss ===
        loss_recon = torch.tensor(0.0, device=pred_seg.device)
        if images is not None and 'recon' in model_output and self.alpha_recon > 0:
            recon_images = model_output['recon']
            loss_recon = self.recon_loss_fn(recon_images, images)
        loss_recon = safe_loss(loss_recon, 'recon')
        losses['recon'] = loss_recon
        
        # === LOSS 5: Object Embedding Loss (Hierarchical Prototype) ===
        loss_obj_emb = torch.tensor(0.0, device=pred_seg.device)
        loss_obj_view_cont = torch.tensor(0.0, device=pred_seg.device)

        if 'obj_emb' in model_output and self.alpha_obj_emb > 0:
            obj_emb = model_output['obj_emb']
            loss_obj_emb = self._hierarchical_prototype_loss(obj_emb, positive_mask)
            loss_obj_view_cont = self._dense_voxel_contrastive_loss_from_concat(obj_emb)

        loss_obj_emb = safe_loss(loss_obj_emb, 'obj_emb')
        loss_obj_view_cont = safe_loss(loss_obj_view_cont, 'obj_view_cont')
        losses['obj_emb'] = loss_obj_emb
        losses['obj_view_cont'] = loss_obj_view_cont
        
        # === LOSS 6: Pixel Contrastive Loss ===
        loss_pixel_con = torch.tensor(0.0, device=pred_seg.device)
        if 'pixel_emb' in model_output and self.alpha_pixel_con > 0:
            pixel_emb = model_output['pixel_emb']
            loss_pixel_con = self.contrastive_loss_fn(
                pixel_emb,
                positive_mask,
                pred_probs=pred_probs
            )
        loss_pixel_con = safe_loss(loss_pixel_con, 'pixel_con')
        losses['pixel_con'] = loss_pixel_con
        
        # === LOSS 7: Total Variation Loss (Smoothness) ===
        loss_var = total_variation_loss(pred_seg)
        loss_var = safe_loss(loss_var, 'total_var')
        losses['total_var'] = loss_var
        
        # === LOSS 8: Small Hole Loss (Morphological) ===
        loss_small_hole = small_hole_loss(pred_probs)
        loss_small_hole = safe_loss(loss_small_hole, 'small_hole')
        losses['small_hole'] = loss_small_hole


        # === LOSS 9: Consistency Loss (between different views of same image) ===
        B = pred_probs.shape[0] // 2
        loss_consistency = F.mse_loss(pred_probs[:B], pred_probs[B:].detach())
        loss_consistency = safe_loss(loss_consistency, 'consistency')
        losses['consistency'] = loss_consistency


        # === Weighted Total Loss ===
        loss_total = (
            self.alpha_seg * losses['segmentation'] +
            self.alpha_edge * losses['edge'] +
            self.alpha_hv * losses['hv'] +
            self.alpha_recon * losses['recon'] +
            self.alpha_obj_emb * losses['obj_emb'] +
            self.alpha_obj_view_cont * losses['obj_view_cont'] +
            self.alpha_pixel_con * losses['pixel_con'] +
            self.alpha_var * losses['total_var'] +
            self.alpha_small_hole * losses['small_hole'] +
            self.alpha_interior * losses['interior_fill'] + 
            self.alpha_consistency * losses['consistency']
        )
        
        loss_total = safe_loss(loss_total, 'total')
        losses['total'] = loss_total
        
        return losses
    
    def _hierarchical_prototype_loss(
        self,
        obj_embeddings: torch.Tensor,
        positive_mask: torch.Tensor,
        temperature: float = 0.1,
    ) -> torch.Tensor:
        """
        Object-level embedding loss using hierarchical prototype clustering.
        Pulls same-class embeddings together, pushes different-class apart.

        Args:
            obj_embeddings: Object embeddings (B, D, H, W)
            positive_mask: Object masks (B, 1, H, W)
            temperature: Temperature for similarity scaling

        Returns:
            Prototype clustering loss (scalar)
        """
        B, D, H, W = obj_embeddings.shape
        device = obj_embeddings.device
        
        if positive_mask.shape[2:] != (H, W):
            positive_mask = F.interpolate(
                positive_mask.float(),
                size=(H, W),
                mode="nearest"
                )


        # Normalize embeddings along channel dimension
        obj_emb_norm = F.normalize(obj_embeddings, dim=1)  # (B, D, H, W)

        loss_total = 0.0
        valid_samples = 0

        for b in range(B):
            emb_flat = obj_emb_norm[b].reshape(D, -1).T  # (H*W, D)
            mask_flat = positive_mask[b].view(-1)        # (H*W,)

            if mask_flat.sum() < 2:
                continue

            # Positive embeddings
            pos_idx = mask_flat.nonzero(as_tuple=True)[0]
            z_pos = emb_flat[pos_idx]  # (N_pos, D)

            # Prototype for positive class
            proto = z_pos.mean(dim=0, keepdim=True)  # (1, D)

            # Compute similarity of all embeddings to prototype
            sim_all = (emb_flat @ proto.T) / temperature  # (H*W, 1)

            # Create labels: positives=1, negatives=0
            labels = mask_flat.to(torch.float32)  # 1 for positive, 0 for negative

            # Compute numerically stable contrastive loss
            # log-sigmoid for positives, log(1-sigmoid) for negatives
            pos_mask = labels.bool()
            neg_mask = ~labels.bool()

            loss_pos = -F.logsigmoid(sim_all[pos_mask]).mean() if pos_mask.any() else 0.0
            loss_neg = -F.logsigmoid(-sim_all[neg_mask]).mean() if neg_mask.any() else 0.0

            loss_b = loss_pos + loss_neg
            loss_total += loss_b
            valid_samples += 1

        return loss_total / max(valid_samples, 1)

    def _dense_voxel_contrastive_loss_from_concat(
        self,
        obj_embeddings: torch.Tensor,
        temperature: float = 0.1,
    ) -> torch.Tensor:
        """
        Dense pixel-wise contrastive loss (InfoNCE style) where
        obj_embeddings is a concatenation of two aligned views:

            [view1_batch, view2_batch]

        Each voxel in view1 is contrasted with the spatially aligned
        voxel in view2, while all other voxels act as negatives.

        Args:
            obj_embeddings: Concatenated embeddings (2B, D, H, W)
            temperature: Temperature scaling

        Returns:
            Dense contrastive loss (scalar)
        """
        B2, D, H, W = obj_embeddings.shape
        device = obj_embeddings.device

        assert B2 % 2 == 0, "Batch size must be even (concatenated views)."
        B = B2 // 2

        # Split views
        z1 = obj_embeddings[:B]
        z2 = obj_embeddings[B:]

        # Flatten spatial dims
        # (B, D, H, W) -> (B*H*W, D)
        z1 = z1.permute(0, 2, 3, 1).reshape(-1, D)
        z2 = z2.permute(0, 2, 3, 1).reshape(-1, D)

        N = z1.shape[0]  # total voxels

        # Similarity matrix
        sim = torch.matmul(z1, z2.T) / temperature  # (N, N)

        # Positive targets are aligned indices
        target = torch.arange(N, device=device)

        # InfoNCE
        loss = F.cross_entropy(sim, target)

        return loss