"""
Multi-task segmentation model for weakly supervised learning.

This module contains the main model architecture for segmentation with auxiliary tasks
such as hypervector regression, image reconstruction, and embedding generation.
"""

import copy
from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
import segmentation_models_pytorch as smp


class PixelEmbeddingHead(nn.Module):
    """
    Head for generating normalized pixel-level embeddings.

    This module takes encoder features and produces L2-normalized embeddings
    for contrastive learning at the pixel level.
    """

    def __init__(self, in_channels: int, embedding_dim: int = 64):
        """
        Initialize the pixel embedding head.

        Args:
            in_channels: Number of input channels from encoder features.
            embedding_dim: Dimensionality of the output embeddings.
        """
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, embedding_dim, 1)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(embedding_dim, embedding_dim, 1)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """
        Forward pass to generate embeddings.

        Args:
            features: Input feature map of shape (B, C, H, W).

        Returns:
            Normalized embeddings of shape (B, embedding_dim, H, W).
        """
        x = self.conv1(features)
        x = self.relu(x)
        x = self.conv2(x)
        norm = torch.norm(x, p=2, dim=1, keepdim=True) + 1e-6
        return x / norm


class MultiTaskSegmentationModel(nn.Module):
    """
    Multi-task segmentation model with auxiliary heads for weakly supervised learning.

    This model is based on UNet++ and includes heads for segmentation, hypervector (HV) regression,
    image reconstruction, object-level embeddings, and pixel-level embeddings.
    """

    def __init__(self, encoder_name: str = "efficientnet-b0", embedding_dim: int = 16):
        """
        Initialize the multi-task segmentation model.

        Args:
            encoder_name: Name of the encoder to use (e.g., 'efficientnet-b0').
            embedding_dim: Dimensionality of embedding projections.
        """
        super().__init__()
        self.model = smp.UnetPlusPlus(
            encoder_name=encoder_name,
            encoder_weights="imagenet",
            in_channels=3,
            classes=1,
            activation=None,
            decoder_attention_type='scse',
            decoder_channels=(16, 16, 16, 16, 16)
        )

        # HV magnitude decoder + segmentation head
        self.decoder_hv = copy.deepcopy(self.model.decoder)
        self.regression_head_hv = copy.deepcopy(self.model.segmentation_head)

        # Reconstruction branch
        bottleneck_channels = self.model.encoder.out_channels[-1]
        self.decoder_recon = nn.Sequential(
            nn.Conv2d(bottleneck_channels, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(64, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(32, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(16, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(16, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(16, 3, kernel_size=3, padding=1),
            nn.Sigmoid()  # output in [0,1]
        )

        self.obj_proj = nn.Conv2d(self.model.encoder.out_channels[-1], embedding_dim, 1)
        self.pixel_proj = PixelEmbeddingHead(self.model.encoder.out_channels[1], embedding_dim)

    def forward(
        self,
        x: torch.Tensor,
        return_embeddings: bool = False,
        return_recon: bool = False,
        return_hv: bool = False,
        return_obj_emb: bool = False,
        return_pixel_emb: bool = False
    ) -> Dict[str, Optional[torch.Tensor]]:
        """
        Forward pass through the model.

        Args:
            x: Input tensor of shape (B, 3, H, W).
            return_embeddings: Whether to return embeddings (deprecated, use specific flags).
            return_recon: Whether to compute and return reconstruction.
            return_hv: Whether to compute and return HV map.
            return_obj_emb: Whether to compute and return object embeddings.
            return_pixel_emb: Whether to compute and return pixel embeddings.

        Returns:
            Dictionary containing requested outputs:
            - 'preds': Segmentation predictions (always included).
            - 'hv_map': HV regression output (if return_hv).
            - 'recon': Reconstructed image (if return_recon).
            - 'obj_emb': Object-level embeddings (if return_obj_emb).
            - 'pixel_emb': Pixel-level embeddings (if return_pixel_emb).
        """
        # Compute encoder features once
        features = self.model.encoder(x)
        dec_out = self.model.decoder(features)
        preds = self.model.segmentation_head(dec_out)

        outputs = {"preds": preds}

        if return_hv:
            hv_dec_out = self.decoder_hv(features)
            hv_map = self.regression_head_hv(hv_dec_out)
            hv_map = torch.sigmoid(hv_map)
            outputs["hv_map"] = hv_map

        if return_recon:
            bottleneck = features[-1]  # bottom of encoder
            recon = self.decoder_recon(bottleneck)  # upsampled reconstruction
            recon = F.interpolate(recon, size=x.shape[-2:], mode='bilinear', align_corners=False)
            outputs["recon"] = recon

        if return_obj_emb:  # Object-level embeddings (low-resolution, coarse)
            obj_emb = self.obj_proj(features[-1])
            obj_emb = F.normalize(obj_emb, dim=1)
            outputs["obj_emb"] = obj_emb

        if return_pixel_emb:  # Pixel-level embeddings (high-resolution)
            pixel_emb = self.pixel_proj(features[1])
            outputs["pixel_emb"] = pixel_emb

        return outputs