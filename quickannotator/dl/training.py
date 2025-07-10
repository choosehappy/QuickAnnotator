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
from .dataset import TileDataset
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

def get_transforms(tile_size): #probably goes...elsewhere
    transforms = A.Compose([
    A.RandomScale(scale_limit=-.1, p=.1),
    A.PadIfNeeded(min_height=tile_size, min_width=tile_size),
    A.VerticalFlip(p=.5),
    A.HorizontalFlip(p=.5),
    A.Blur(p=.5),
    # # Downscale(p=.25, scale_min=0.64, scale_max=0.99),
    A.GaussNoise(p=.5, var_limit=(10.0, 50.0)),
    # A.GridDistortion(p=.5, num_steps=5, distort_limit=(-0.3, 0.3),
    #                 border_mode=cv2.BORDER_REFLECT),
    # A.ISONoise(p=.5, intensity=(0.1, 0.5), color_shift=(0.01, 0.05)),
    # A.RandomBrightnessContrast(p=0.5, brightness_limit=(-0.2, 0.2), contrast_limit=(-0.2, 0.2), brightness_by_max=True),
    # A.RandomGamma(p=.5, gamma_limit=(80, 120), eps=1e-07),
    # A.MultiplicativeNoise(p=.5, multiplier=(0.9, 1.1), per_channel=True, elementwise=True),
    # A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=10, val_shift_limit=10, p=.9),
    A.Rotate(p=1, border_mode=cv2.BORDER_REFLECT),
    A.RandomCrop(tile_size, tile_size),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),  # Normalization
    ToTensorV2()])
    return transforms



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

    #TODO: all these from project settings
    boost_count = 5
    batch_size_train=4
    batch_size_infer=4
    edge_weight=1_000
    num_workers=0 #TODO:set to num of CPUs? or...# of CPUs/ divided by # of classes or something...challenge - one started can't change. maybe set to min(batch_size train, ??) 
    

    # Set device
    if torch.cuda.is_available():
        localrank=ray.train.get_context().get_local_rank()
        device=torch.device('cuda',localrank)
    else:
        device= "cpu"

    dataset=TileDataset(annotation_class_id,
                        edge_weight=edge_weight, transforms=get_transforms(tile_size), 
                        boost_count=boost_count)

    dataloader = DataLoader(dataset, batch_size=batch_size_train, shuffle=False, num_workers=num_workers) #NOTE: for dataset of type iter - shuffle must == False

    #model = smp.Unet(encoder_name="timm-mobilenetv3_small_100", encoder_weights="imagenet", in_channels=3, classes=1) #TODO: this should all be a setting
    model = smp.Unet(encoder_name="efficientnet-b0", encoder_weights="imagenet", 
                 decoder_channels=(64, 64, 64, 32, 16), in_channels=3, classes=1, encoder_freeze=True )
    
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


    criterion = nn.BCEWithLogitsLoss(reduction='none', ).cuda() # TODO: make this a setting and provide other loss function options (DICE loss?)
    optimizer = optim.NAdam(model.parameters(), lr=0.001, weight_decay=1e-2) #TODO: this should be a setting
    
    scaler = torch.amp.GradScaler("cuda")

    # print(summary(model, (3, tile_size, tile_size))) #TODO: log this
    # TODO: why does the above line produce an error: RuntimeError: Input type (torch.cuda.FloatTensor) and weight type (torch.FloatTensor) should be the same
    #--- freeze encoder weights
    for param in model.encoder.parameters():
        param.requires_grad = False
        
    for name, param in model.named_parameters():
        if not param.requires_grad:
            logger.info(f"{name} is frozen")
    #-----


    
    #model = model.half() #TODO: test with .half()
    model=ray.train.torch.prepare_model(model,device)
    model.train()


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
            images, masks, weights = next(iter(dataloader))
            #print ("post next iter")
            images = images.half().to(device) #TODO: test with .half()
            masks = masks.to(device) #these should remain as uint8 - which is both more correct and half the size of a float16
            weights = weights.to(device)
            #print ("post copy ")
            
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                optimizer.zero_grad()
                outputs = model(images)
                
                loss = criterion(outputs, masks.float())
                loss = (loss * (edge_weight ** weights).type_as(loss)).mean()
                
                positive_mask = (masks == 1).float()
                unlabeled_mask = (masks == 0).float()
                
                positive_loss = 1.0 * (loss * positive_mask).mean()
                unlabeled_loss = .1 * (loss * unlabeled_mask).mean()
                
                loss_total = positive_loss + unlabeled_loss
            # loss_total.backward()
            # optimizer.step()
            
            scaler.scale(loss_total).backward()

            scaler.step(optimizer)
            scaler.update()


            running_loss.append(loss_total.item())
            
            writer.add_scalar(f'loss/loss', loss, niter_total)
            writer.add_scalar(f'loss/positive_loss', positive_loss, niter_total)
            writer.add_scalar(f'loss/unlabeled_loss', unlabeled_loss, niter_total)
            writer.add_scalar(f'loss/loss_total', loss_total, niter_total)

            #print ("losses:\t",loss_total,positive_mask.sum(),positive_loss,unlabeled_loss)
            
            last_save+=1
            if last_save>50:
                logger.info(f"niter_total [{niter_total}], Loss: {sum(running_loss)/len(running_loss)}")
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