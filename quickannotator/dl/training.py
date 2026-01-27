import logging
import segmentation_models_pytorch as smp
import torch
from torch.utils.data import DataLoader
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm
import ray

from torchsummary import summary
import datetime
from quickannotator.dl.inference import run_inference
from quickannotator.db.crud.tile import TileStoreFactory
from quickannotator.db.crud.annotation_class import build_actor_name
from .dataset import TileDataset, PatchedDataset, compute_hv_map
from .model import UNetMultiTask
from .loss import MultiTaskLoss
from .dl_config import DLConfig, get_default_config, get_augmentation_transforms
import io
import albumentations as A
from albumentations.pytorch import ToTensorV2
import cv2
from safetensors.torch import save_file, load_file
from quickannotator.db.fsmanager import fsmanager
import quickannotator.constants as constants
import os
from quickannotator.db.logging import LoggingManager

from torch.utils.tensorboard import SummaryWriter

def get_transforms_from_config(tile_size, dl_config: DLConfig = None):
    """Get augmentation transforms from configuration or use default."""
    if dl_config is None:
        dl_config = get_default_config()
    return get_augmentation_transforms(tile_size, dl_config.augmentation)



def train_pred_loop(config):
    #---------AJ Place holder code - DO NOT REMOVE
    # #print (f"{os.environ['CUDA_VISIBLE_DEVICES']=}")
    # localrank=ray.train.get_context().get_local_rank()
    # worldsize=ray.train.get_context().get_local_world_size()
    # #print ("my local rank",localrank)
    # #print ("my local worldsize",worldsize)

    # noderank=ray.train.get_context().get_node_rank()
    # worldrank=ray.train.get_context().get_world_rank()
    # #print ("my node rank",noderank)
    # #print ("my worldrank",worldrank)
    
    # #print ("creating model")
    # model = resnet18(num_classes=10)

    # #print ("figuring out local device")
    # cuda_dev=torch.device('cuda',localrank)
    # #print ("local device is: ",cuda_dev)
    # #print (" now moving")
    # model.to(cuda_dev)
    
    # #print ("prepping model")
    # #model=ray.train.torch.prepare_model(model,cuda_dev)
    # model=ray.train.torch.prepare_model(model,move_to_device=False)
    #---------
    logger = LoggingManager.init_logger(constants.LoggerNames.RAY.value)
    logger.info("Initialized train_pred_loop")
    #TODO: likely need to accept here the checkpoint location
    annotation_class_id = config["annotation_class_id"] # --- this should result in a catastrophic failure if not provided
    tile_size = config["tile_size"] #probably this as well
    magnification = config["magnification"] #probably this as well
    actor_name = build_actor_name(annotation_class_id)
    logger.info(f"Actor name: {actor_name}")

    # Load or create default configuration
    dl_config = get_default_config()
    boost_count = dl_config.boost_count
    batch_size_train = dl_config.data.batch_size
    batch_size_infer = dl_config.batch_size_infer
    edge_weight = dl_config.edge_weight ##??
    num_workers = dl_config.data.num_workers
    patch_size = dl_config.data.patch_size
    
    logger.info(f"Training config: batch_size={batch_size_train}, patch_size={patch_size}, edge_weight={edge_weight}") 
    

    # Set device
    if torch.cuda.is_available():
        localrank=ray.train.get_context().get_local_rank()
        device=torch.device('cuda',localrank)
    else:
        device= "cpu"

    # Create tile dataset and wrap with PatchedDataset for patch-based training
    tile_dataset = TileDataset(
        annotation_class_id,
        edge_weight=edge_weight,
        transforms=get_transforms_from_config(patch_size, dl_config),
        boost_count=boost_count
    )
    
    # Wrap with PatchedDataset to extract patches from tiles with HV maps
    patched_dataset = PatchedDataset(
        tile_dataset=tile_dataset,
        patch_size=patch_size,
        transforms=None  # Transforms already applied in TileDataset
    )

    dataloader = DataLoader(
        patched_dataset,
        batch_size=batch_size_train,
        shuffle=False,  # IterableDataset doesn't support shuffle
        num_workers=num_workers
    )

    # Create model - use the new multi-task model with config parameters
    model = UNetMultiTask(
        encoder_name=dl_config.model.encoder_name,
        embedding_dim=dl_config.model.embedding_dim
    )
    
    # Load the model weights
    checkpoint_path = get_checkpoint_filepath(annotation_class_id)
    if os.path.exists(checkpoint_path):
        logger.info(f"Loading model from {checkpoint_path}")
        try:
            checkpoint = load_file(checkpoint_path)  # Use safetensors to load the checkpoint
            model.load_state_dict(checkpoint, strict=False)  # Use strict=False if keys mismatch
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            raise
    else:
        logger.info(f"No checkpoint found at {checkpoint_path}, starting from scratch.")


    # Create multi-task loss with all 8 components from configuration
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
        pos_thresh=dl_config.loss.pos_thresh
    )
    
    # Create optimizer from configuration
    optimizer = optim.NAdam(
        model.parameters(),
        lr=dl_config.optimizer.learning_rate,
        weight_decay=dl_config.optimizer.weight_decay
    )
    
    scaler = torch.amp.GradScaler("cuda")

    # print(summary(model, (3, tile_size, tile_size))) #TODO: log this
    # TODO: why does the above line produce an error: RuntimeError: Input type (torch.cuda.FloatTensor) and weight type (torch.FloatTensor) should be the same
    
    #model = model.half() #TODO: test with .half()
    model=ray.train.torch.prepare_model(model,device)
    model.train()
    
    # Freeze encoder weights for transfer learning
    for param in model.model.encoder.parameters():
        param.requires_grad = False
        
    for name, param in model.named_parameters():
        if not param.requires_grad:
            logger.info(f"{name} is frozen")

    running_loss = []
    
    writer = SummaryWriter(log_dir=get_log_filepath(annotation_class_id))
    last_save = 0
    niter_total = 0 
    #print ("pre actor get")
    myactor = ray.get_actor(actor_name)
    #print ("post actor get")
    while ray.get(myactor.getProcRunningSince.remote()):    # procRunningSince will be None if the DL processing is to be stopped.
        tilestore = TileStoreFactory.get_tilestore()
        while tiles := tilestore.get_pending_inference_tiles(annotation_class_id, batch_size_infer):
            logger.info(f"Running inference on {len(tiles)} tiles for annotation class {annotation_class_id}")
            tileids = [tile.tile_id for tile in tiles]
            logger.info(f"Tiles to process: {tileids}")
            #print (f"running inference on {len(tiles)}")
            run_inference(device, model, tiles)
            
        logger.info(f"No more STARTPROCESSING tiles for annotation class {annotation_class_id}. Entering training loop.")
        if ray.get(myactor.getEnableTraining.remote()):
            #print ("in train loop")
            niter_total += 1
            batch_data = next(iter(dataloader))
            
            # Unpack patch batch: (patch_image, patch_mask, patch_weight, hv_map)
            images = batch_data[0]
            masks = batch_data[1]
            # Note: weights (batch_data[2]) currently unused - reserved for future per-sample weighting
            hv_maps = batch_data[3]
            
            # Move to device and normalize images to [0, 1]
            images = images.half().to(device) / 255.0
            masks = masks.to(device)
            hv_maps = hv_maps.to(device)
            
            with torch.autocast(device_type="cuda", dtype=torch.float16):
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
                # MultiTaskLoss.forward() returns dict with 'total' and individual components
                losses_dict = criterion(
                    model_output=model_output,
                    positive_mask=masks,
                    target_hv=hv_maps,
                    images=images,  # Required for reconstruction loss
                    pred_probs=torch.sigmoid(model_output['preds'])
                )
                loss_total = losses_dict['total']

            scaler.scale(loss_total).backward()
            
            # Optional gradient clipping for stability
            if dl_config.optimizer.grad_clip is not None:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), dl_config.optimizer.grad_clip)
            
            scaler.step(optimizer)
            scaler.update()

            running_loss.append(loss_total.item())
            
            # Log total loss and all 8 components to TensorBoard for comprehensive monitoring
            def _to_scalar(val):
                """Helper to safely extract scalar from tensor or return float."""
                return val.item() if isinstance(val, torch.Tensor) else float(val)
            
            writer.add_scalar('loss/total', loss_total.item(), niter_total)
            writer.add_scalar('loss/segmentation', _to_scalar(losses_dict['segmentation']), niter_total)
            writer.add_scalar('loss/edge', _to_scalar(losses_dict['edge']), niter_total)
            writer.add_scalar('loss/hv', _to_scalar(losses_dict['hv']), niter_total)
            writer.add_scalar('loss/recon', _to_scalar(losses_dict['recon']), niter_total)
            writer.add_scalar('loss/obj_emb', _to_scalar(losses_dict['obj_emb']), niter_total)
            writer.add_scalar('loss/pixel_con', _to_scalar(losses_dict['pixel_con']), niter_total)
            writer.add_scalar('loss/total_var', _to_scalar(losses_dict['total_var']), niter_total)
            writer.add_scalar('loss/small_hole', _to_scalar(losses_dict['small_hole']), niter_total)

            #print ("losses:\t",loss_total,positive_mask.sum(),positive_loss,unlabeled_loss)
            
            last_save+=1
            if last_save>50:
                logger.info(f"niter_total [{niter_total}], Loss: {sum(running_loss)/len(running_loss)}")
                logger.info(f"  - Segmentation: {_to_scalar(losses_dict['segmentation']):.4f}")
                logger.info(f"  - Edge: {_to_scalar(losses_dict['edge']):.4f}")
                logger.info(f"  - HV: {_to_scalar(losses_dict['hv']):.4f}")
                logger.info(f"  - Reconstruction: {_to_scalar(losses_dict['recon']):.4f}")
                logger.info(f"  - Object Embedding: {_to_scalar(losses_dict['obj_emb']):.4f}")
                logger.info(f"  - Pixel Contrastive: {_to_scalar(losses_dict['pixel_con']):.4f}")
                logger.info(f"  - Total Variation: {_to_scalar(losses_dict['total_var']):.4f}")
                logger.info(f"  - Small Hole: {_to_scalar(losses_dict['small_hole']):.4f}")
                running_loss=[]

                logger.info("Saving model checkpoint")  # Use logger instead of print
                                 #another potentially more interesting option is to do both, save on a regular basis (since if we things crash we can revert back othe nearest checkpoint\
                                 #but as well give the user in the front end a dropdown which enables them to select which model checkpoint they want to use? we had somethng similar in QAv1
                                 #that said, this is likely a more advanced features and not very "apple like" since it would require explaining to the user when/why/how they should use the different models
                                 #maybe suggest avoiduing for now --- lets just save the last one
                checkpoint_path = get_checkpoint_filepath(annotation_class_id)
                save_file(model.state_dict(), checkpoint_path)
                logger.info(f"Model checkpoint saved to {checkpoint_path}")
                last_save = 0
                
    logger.info("Exiting training!")


def get_checkpoint_filepath(annotation_class_id: int):
    """
    Returns the path to the model checkpoint for the given annotation class ID.
    """
    savepath = fsmanager.nas_write.get_class_checkpoint_path(annotation_class_id)
    if not os.path.exists(savepath):
        os.makedirs(savepath, exist_ok=True)
    return os.path.join(savepath, constants.CHECKPOINT_FILENAME)


def get_log_filepath(annotation_class_id: int):
    """
    Returns the path to the log file for the given annotation class ID.
    """
    savepath = fsmanager.nas_write.get_logs_path(annotation_class_id)
    if not os.path.exists(savepath):
        os.makedirs(savepath, exist_ok=True)
    filename = datetime.datetime.now().strftime('%b%d_%H-%M-%S')
    return os.path.join(savepath, filename + ".log")