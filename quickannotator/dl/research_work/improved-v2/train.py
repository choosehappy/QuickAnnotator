
# %%

"""
Improved-v2 Reference Training Implementation

Adapted from production training.py for local filesystem-based research workflow.
This is a minimal wrapper that reuses all production DL modules and training logic,
with Ray/Database dependencies removed for standalone execution.

Key features:
  - Full-featured training with AMP, gradient clipping, logging
  - All 8-component multi-task loss from production code
  - Checkpoint management and TensorBoard logging
  - Filesystem-based dataset loading (no database required)
"""

import random
import sys
from pathlib import Path

# Add the QuickAnnotator root to Python path
project_root = Path(__file__).resolve().parents[4]  # Goes up 4 levels to /home/janowczy/research/QuickAnnotator
sys.path.insert(0, str(project_root))

import logging
import os
import sys
import glob
from pathlib import Path
from typing import Tuple, Optional
import datetime

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard.writer import SummaryWriter
from torch.cuda.amp.grad_scaler import GradScaler
import torch.amp
from torch.nn.utils.clip_grad import clip_grad_norm_
from tqdm import tqdm

# Import from main DL package - single source of truth
from quickannotator.dl.model import UNetMultiTask
from quickannotator.dl.loss import MultiTaskLoss
#from quickannotator.dl.dataset import PatchedDataset
from quickannotator.dl.patcheddataset import PatchedDataset
from quickannotator.dl.dl_config import DLConfig, get_default_config, get_augmentation_transforms

from datasets import FilesystemDataset


# Configure logging for local training
def setup_logging(log_dir: str):
    """Setup logging for local training."""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"train_{datetime.datetime.now().strftime('%b%d_%H-%M-%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def get_checkpoint_filepath(checkpoint_dir: str):
    """Returns the path to the model checkpoint."""
    os.makedirs(checkpoint_dir, exist_ok=True)
    return os.path.join(checkpoint_dir, "model_latest.pt")


def train(
    data_dir: Path = Path("./images"),
    checkpoint_dir: str = "./checkpoints",
    log_dir: str = "./logs",
    num_epochs: int = 100,
    dl_config: Optional[DLConfig] = None,
):
    """
    Main training loop for local filesystem-based training.
    
    Adapted from production train_pred_loop() with Ray/Database removed.

    Args:
        data_dir: Directory containing image patches (*_img.png and *_mask.png).
        checkpoint_dir: Directory to save model checkpoints.
        log_dir: Directory for TensorBoard logs and training logs.
        num_epochs: Number of training epochs.
        dl_config: DLConfig object. If None, uses defaults.
    """
    if dl_config is None:
        dl_config = get_default_config()

    
    # Setup logging
    logger = setup_logging(log_dir)
    logger.info("Initialized improved-v2 training")
    logger.info(f"Training config: batch_size={dl_config.data.batch_size}, patch_size={dl_config.data.patch_size}")

    # Set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")


    # Create filesystem dataset and wrap with PatchedDataset
    img_paths = sorted(glob.glob(str(data_dir / "*_img.png")))
    mask_paths = sorted(glob.glob(str(data_dir / "*_mask.png")))
    
    if len(img_paths) == 0:
        logger.error(f"No images found in {data_dir}")
        raise FileNotFoundError(f"No images found in {data_dir}")

    logger.info(f"Found {len(img_paths)} image-mask pairs")
    

    # Create filesystem dataset and wrap with production PatchedDataset
    filesystem_dataset = FilesystemDataset(img_paths, mask_paths)
    patched_dataset = PatchedDataset(
        tile_dataset=filesystem_dataset,  # type: ignore - FilesystemDataset duck-types TileDataset
        patch_size=dl_config.data.patch_size,
        stride=dl_config.data.stride,
        shuffle_patches=dl_config.data.shuffle_patches,
        transforms=get_augmentation_transforms(dl_config.data.patch_size, dl_config.augmentation)
    )

    dataloader = DataLoader(
        patched_dataset,
        batch_size=dl_config.data.batch_size,
        shuffle=False,  # IterableDataset doesn't support shuffle
        num_workers=dl_config.data.num_workers
    )

    # Create model
    model = UNetMultiTask(
        encoder_name=dl_config.model.encoder_name,
        embedding_dim=dl_config.model.embedding_dim
    )

    # Load checkpoint if exists
    checkpoint_path = get_checkpoint_filepath(checkpoint_dir)
    if os.path.exists(checkpoint_path):
        logger.info(f"Loading model from {checkpoint_path}")
        try:
            checkpoint = torch.load(checkpoint_path, map_location=device)
            model.load_state_dict(checkpoint, strict=False)
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            raise
    else:
        logger.info(f"Starting from scratch (no checkpoint at {checkpoint_path})")

    model = model.to(device)
    model.train()

    # Conditionally freeze encoder weights for transfer learning
    if dl_config.model.encoder_freeze:
        for param in model.model.encoder.parameters():
            param.requires_grad = False
        logger.info("Encoder weights frozen for transfer learning")

    for name, param in model.named_parameters():
        if not param.requires_grad:
            logger.info(f"Frozen parameter: {name}")

    # Create multi-task loss with all 8 components
    criterion = MultiTaskLoss(
        alpha_seg=dl_config.loss.alpha_seg,
        alpha_edge=dl_config.loss.alpha_edge,
        alpha_hv=dl_config.loss.alpha_hv,
        alpha_recon=dl_config.loss.alpha_recon,
        alpha_obj_emb=dl_config.loss.alpha_obj_emb,
        alpha_pixel_con=dl_config.loss.alpha_pixel_con,
        alpha_var=dl_config.loss.alpha_var,
        alpha_small_hole=dl_config.loss.alpha_small_hole,
        bce_dice_weight=dl_config.loss.bce_dice_weight,
        temperature=dl_config.loss.temperature,
        max_samples=dl_config.loss.max_samples,
        pos_thresh=dl_config.loss.pos_thresh,
        post_process_pseudo=dl_config.loss.post_process_pseudo,
        max_size=dl_config.loss.max_size,
        max_hole_size=dl_config.loss.max_hole_size,
        smooth_pseudo=dl_config.loss.smooth_pseudo,
        smooth_radius=dl_config.loss.smooth_radius
    )

    # Create optimizer
    optimizer = optim.AdamW(
        model.parameters(),
        lr=dl_config.optimizer.learning_rate,
        weight_decay=dl_config.optimizer.weight_decay,
        betas=(dl_config.optimizer.beta1, dl_config.optimizer.beta2)
    )

    # Setup AMP gradient scaler
    scaler = GradScaler() if torch.cuda.is_available() else None

    # Setup TensorBoard
    writer = SummaryWriter(log_dir=log_dir)

    running_loss = []
    last_save = 0
    niter_total = 0

    def _to_scalar(val):
        """Helper to safely extract scalar from tensor or return float."""
        return val.item() if isinstance(val, torch.Tensor) else float(val)

    logger.info("Starting training loop")

    # Training loop
    for epoch in range(num_epochs):
        for batch_idx, batch_data in enumerate(tqdm(dataloader, desc=f"Epoch {epoch+1}/{num_epochs}")):
            niter_total += 1

            # Unpack patch batch: (patch_image, patch_mask, hv_map)
            images = batch_data[0]
            masks = batch_data[1]
            hv_maps = batch_data[2]

            # Move to device and normalize images to [0, 1]
            images = images.to(device) / 255.0
            masks = masks.to(device)
            hv_maps = hv_maps.to(device)

            # Forward pass with AMP
            if torch.cuda.is_available() and scaler is not None:
                with torch.amp.autocast('cuda', dtype=torch.float16, enabled=True):
                    optimizer.zero_grad()

                    # Forward pass with ALL auxiliary tasks enabled
                    model_output = model(
                        images,
                        return_recon=True,
                        return_hv=True,
                        return_obj_emb=True,
                        return_pixel_emb=True
                    )

                    # Compute 8-component multi-task loss
                    losses_dict = criterion(
                        model_output=model_output,
                        positive_mask=masks,
                        target_hv=hv_maps,
                        images=images,
                        pred_probs=torch.sigmoid(model_output['preds'])
                    )
                    loss_total = losses_dict['total']

                scaler.scale(loss_total).backward()  # type: ignore - scaler.scale returns Tensor

                # Optional gradient clipping for stability
                if dl_config.optimizer.grad_clip is not None:
                    scaler.unscale_(optimizer)
                    clip_grad_norm_(model.parameters(), dl_config.optimizer.grad_clip)

                scaler.step(optimizer)
                scaler.update()
            else:
                # CPU mode without AMP
                optimizer.zero_grad()

                model_output = model(
                    images,
                    return_recon=True,
                    return_hv=True,
                    return_obj_emb=True,
                    return_pixel_emb=True
                )

                losses_dict = criterion(
                    model_output=model_output,
                    positive_mask=masks,
                    target_hv=hv_maps,
                    images=images,
                    pred_probs=torch.sigmoid(model_output['preds'])
                )
                loss_total = losses_dict['total']

                loss_total.backward()

                if dl_config.optimizer.grad_clip is not None:
                    clip_grad_norm_(model.parameters(), dl_config.optimizer.grad_clip)

                optimizer.step()

            running_loss.append(loss_total.item())

            # Log to TensorBoard
            writer.add_scalar('loss/total', loss_total.item(), niter_total)
            writer.add_scalar('loss/segmentation', _to_scalar(losses_dict['segmentation']), niter_total)
            writer.add_scalar('loss/seg_bce_pos', _to_scalar(losses_dict['seg_bce_pos']), niter_total)
            writer.add_scalar('loss/seg_dice', _to_scalar(losses_dict['seg_dice']), niter_total)
            writer.add_scalar('loss/seg_bce_bg', _to_scalar(losses_dict['seg_bce_bg']), niter_total)
            writer.add_scalar('loss/edge', _to_scalar(losses_dict['edge']), niter_total)
            writer.add_scalar('loss/hv', _to_scalar(losses_dict['hv']), niter_total)
            writer.add_scalar('loss/recon', _to_scalar(losses_dict['recon']), niter_total)
            writer.add_scalar('loss/obj_emb', _to_scalar(losses_dict['obj_emb']), niter_total)
            writer.add_scalar('loss/pixel_con', _to_scalar(losses_dict['pixel_con']), niter_total)
            writer.add_scalar('loss/total_var', _to_scalar(losses_dict['total_var']), niter_total)
            writer.add_scalar('loss/small_hole', _to_scalar(losses_dict['small_hole']), niter_total)


            # Images (slow, so less frequent)
            if niter_total % (dl_config.training.save_checkpoint_interval) == 0:
                writer.add_image("imgs/img", images[0], niter_total)
                if 'recon' in model_output and model_output['recon'] is not None:
                    writer.add_image("imgs/recon", model_output['recon'][0], niter_total)
                preds = torch.sigmoid(model_output['preds'])
                writer.add_image("imgs/preds", preds[0], niter_total)
                writer.add_image("imgs/preds_thresh", (preds[0] >= dl_config.loss.pos_thresh).float(), niter_total)
                writer.add_image("imgs/masks", masks[0].float(), niter_total)
                if 'hv' in model_output and model_output['hv'] is not None:
                    writer.add_image("imgs/hv_map", model_output['hv'][0], niter_total)

            last_save += 1

            # Log periodically
            if last_save > dl_config.training.save_checkpoint_interval:
                avg_loss = sum(running_loss) / len(running_loss)
                logger.info(f"Epoch [{epoch+1}/{num_epochs}], Iter [{niter_total}], Loss: {avg_loss:.4f}")
                logger.info(f"  - Segmentation: {_to_scalar(losses_dict['segmentation']):.4f}")
                logger.info(f"    - BCE Pos: {_to_scalar(losses_dict['seg_bce_pos']):.4f}")
                logger.info(f"    - Dice: {_to_scalar(losses_dict['seg_dice']):.4f}")
                logger.info(f"    - BCE BG: {_to_scalar(losses_dict['seg_bce_bg']):.4f}")
                logger.info(f"  - Edge: {_to_scalar(losses_dict['edge']):.4f}")
                logger.info(f"  - HV: {_to_scalar(losses_dict['hv']):.4f}")
                logger.info(f"  - Reconstruction: {_to_scalar(losses_dict['recon']):.4f}")
                logger.info(f"  - Object Embedding: {_to_scalar(losses_dict['obj_emb']):.4f}")
                logger.info(f"  - Pixel Contrastive: {_to_scalar(losses_dict['pixel_con']):.4f}")
                logger.info(f"  - Total Variation: {_to_scalar(losses_dict['total_var']):.4f}")
                logger.info(f"  - Small Hole: {_to_scalar(losses_dict['small_hole']):.4f}")

                running_loss = []

                # Save checkpoint
                logger.info("Saving model checkpoint")
                checkpoint_path = get_checkpoint_filepath(checkpoint_dir)
                torch.save(model.state_dict(), checkpoint_path)
                logger.info(f"Model checkpoint saved to {checkpoint_path}")
                last_save = 0

    logger.info("Training complete!")
    writer.close()


if __name__ == "__main__":
    # Example usage - customize as needed
    config = get_default_config()
    config.data.batch_size = 8
    config.data.num_workers = 8

    train(
        data_dir=Path("/home/janowczy/research/quickannotator_dl/images"),
        checkpoint_dir="./checkpoints",
        log_dir="./logs/improved-v2",
        num_epochs=10,
        dl_config=config,
    )

