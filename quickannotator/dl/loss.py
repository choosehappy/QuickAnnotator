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
    
    def forward(self, pred_hv: torch.Tensor, target_hv: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Compute HV regression loss.
        
        Args:
            pred_hv: Predicted HV maps of shape (B, 1, H, W).
            target_hv: Target HV maps of shape (B, 1, H, W).
            mask: Optional mask to apply (B, 1, H, W). Only compute loss on masked regions.
            
        Returns:
            HV regression loss.
        """
        if mask is not None:
            # Only compute loss on positive regions
            pred_hv_masked = pred_hv * mask
            target_hv_masked = target_hv * mask
            
            # Compute MSE only on masked regions
            mse = ((pred_hv_masked - target_hv_masked) ** 2 * mask).sum() / (mask.sum() + 1e-8)
            return mse
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
    Comprehensive multi-task loss combining 8 auxiliary losses:
    1. Segmentation (weakly-supervised with pseudo-labels)
    2. Edge-aware segmentation
    3. HV regression (distance maps)
    4. Image reconstruction
    5. Object-level embedding (hierarchical prototype clustering)
    6. Pixel-level contrastive learning
    7. Total variation (smoothness regularization)
    8. Small hole morphological regularization
    
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
        bce_dice_weight: float = 0.5,
        temperature: float = 0.1,
        max_samples: int = 512,
        pos_thresh: float = 0.5,
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
            bce_dice_weight: Balance between BCE and Dice in segmentation.
            temperature: Temperature for contrastive similarity.
            max_samples: Max samples for contrastive learning.
            pos_thresh: Threshold for positive predictions.
        """
        super().__init__()
        self.alpha_seg = alpha_seg
        self.alpha_edge = alpha_edge
        self.alpha_hv = alpha_hv
        self.alpha_recon = alpha_recon
        self.alpha_obj_emb = alpha_obj_emb
        self.alpha_pixel_con = alpha_pixel_con
        self.alpha_var = alpha_var
        self.alpha_small_hole = alpha_small_hole
        self.pos_thresh = pos_thresh
        
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
        device = positive_mask.device
        losses = {}
        
        # === LOSS 1: Segmentation (Weakly-Supervised) ===
        pred_seg = model_output['preds']
        if pred_probs is None:
            pred_probs = torch.sigmoid(pred_seg)
        
        # Generate pseudo-labels for weakly-supervised learning
        pseudo_pos, pseudo_neg = self.seg_loss_fn.generate_pseudo_labels(
            pred_probs, positive_mask,
            threshold_pos=self.pos_thresh,
            post_process=True,
            min_size=10,
            min_hole_size=10,
            smooth=True,
            smooth_radius=3
        )
        loss_seg = self.seg_loss_fn(pred_seg, positive_mask, pseudo_pos=pseudo_pos, pseudo_neg=pseudo_neg)
        losses['segmentation'] = loss_seg
        
        # === LOSS 2: Edge-Aware Loss ===
        loss_edge = edge_loss(positive_mask, pred_seg)
        losses['edge'] = loss_edge
        
        # === LOSS 3: HV Regression Loss ===
        loss_hv = 0.0
        if 'hv_map' in model_output and self.alpha_hv > 0:
            pred_hv = model_output['hv_map']
            loss_hv = self.hv_loss_fn(pred_hv, target_hv, mask=positive_mask)
        losses['hv'] = loss_hv
        
        # === LOSS 4: Image Reconstruction Loss ===
        loss_recon = 0.0
        if images is not None and 'recon' in model_output and self.alpha_recon > 0:
            recon_images = model_output['recon']
            loss_recon = self.recon_loss_fn(recon_images, images)
        losses['recon'] = loss_recon
        
        # === LOSS 5: Object Embedding Loss (Hierarchical Prototype) ===
        loss_obj_emb = 0.0
        if 'obj_emb' in model_output and self.alpha_obj_emb > 0:
            obj_emb = model_output['obj_emb']
            loss_obj_emb = self._hierarchical_prototype_loss(obj_emb, positive_mask)
        losses['obj_emb'] = loss_obj_emb
        
        # === LOSS 6: Pixel Contrastive Loss ===
        loss_pixel_con = 0.0
        if 'pixel_emb' in model_output and self.alpha_pixel_con > 0:
            pixel_emb = model_output['pixel_emb']
            loss_pixel_con = self.contrastive_loss_fn(
                pixel_emb,
                positive_mask,
                pred_probs=pred_probs
            )
        losses['pixel_con'] = loss_pixel_con
        
        # === LOSS 7: Total Variation Loss (Smoothness) ===
        loss_var = total_variation_loss(pred_seg)
        losses['total_var'] = loss_var
        
        # === LOSS 8: Small Hole Loss (Morphological) ===
        loss_small_hole = small_hole_loss(pred_probs)
        losses['small_hole'] = loss_small_hole
        
        # === Weighted Total Loss ===
        loss_total = (
            self.alpha_seg * losses['segmentation'] +
            self.alpha_edge * losses['edge'] +
            self.alpha_hv * losses['hv'] +
            self.alpha_recon * losses['recon'] +
            self.alpha_obj_emb * losses['obj_emb'] +
            self.alpha_pixel_con * losses['pixel_con'] +
            self.alpha_var * losses['total_var'] +
            self.alpha_small_hole * losses['small_hole']
        )
        
        # Safety check for NaN/Inf losses
        if torch.isnan(loss_total) or torch.isinf(loss_total):
            raise ValueError(f"Loss is NaN/Inf! Check individual loss components for issues.")
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
            Prototype clustering loss
        """
        B, D, H, W = obj_embeddings.shape
        device = obj_embeddings.device
        
        # Normalize embeddings
        obj_emb_norm = F.normalize(obj_embeddings, dim=1)  # (B, D, H, W)
        
        loss_total = 0.0
        valid_samples = 0
        
        for b in range(B):
            emb_flat = obj_emb_norm[b].reshape(D, -1).T  # (H*W, D)
            mask_flat = positive_mask[b].view(-1)  # (H*W,)
            
            if mask_flat.sum() < 2:
                continue
            
            # Positive samples (foreground)
            pos_idx = mask_flat.nonzero(as_tuple=True)[0]
            z_pos = emb_flat[pos_idx]  # (N_pos, D)
            
            # Prototype (mean of positive embeddings)
            proto = z_pos.mean(dim=0, keepdim=True)  # (1, D)
            
            # Similarity of positive samples to prototype
            sim_pos = (z_pos @ proto.T) / temperature  # (N_pos, 1)
            
            # Negative samples (background)
            neg_idx = (~mask_flat).nonzero(as_tuple=True)[0]
            if neg_idx.numel() > 0:
                z_neg = emb_flat[neg_idx]  # (N_neg, D)
                sim_neg = (z_neg @ proto.T) / temperature  # (N_neg, 1)
                
                # InfoNCE-style loss
                pos_loss = -torch.log(torch.sigmoid(sim_pos).mean() + 1e-8)
                neg_loss = -torch.log(1.0 - torch.sigmoid(sim_neg).mean() + 1e-8)
                loss_b = pos_loss + neg_loss
            else:
                loss_b = -torch.log(torch.sigmoid(sim_pos).mean() + 1e-8)
            
            loss_total += loss_b
            valid_samples += 1
        
        return loss_total / max(valid_samples, 1)
