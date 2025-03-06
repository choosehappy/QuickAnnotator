import segmentation_models_pytorch as smp
import torch
from torch.utils.data import DataLoader
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm
import ray

from quickannotator.dl.inference import run_inference, getPendingInferenceTiles
from .dataset import TileDataset
import io
import albumentations as A
from albumentations.pytorch import ToTensorV2
import cv2
from safetensors.torch import save_file

def get_transforms(tile_size): #probably goes...elsewhere
    transforms = A.Compose([
    A.RandomScale(scale_limit=0.1, p=.9),
    A.PadIfNeeded(min_height=tile_size, min_width=tile_size),
    A.VerticalFlip(p=.5),
    A.HorizontalFlip(p=.5),
    A.Blur(p=.5),
    # Downscale(p=.25, scale_min=0.64, scale_max=0.99),
    A.GaussNoise(p=.5, var_limit=(10.0, 50.0)),
    A.GridDistortion(p=.5, num_steps=5, distort_limit=(-0.3, 0.3),
                    border_mode=cv2.BORDER_REFLECT),
    A.ISONoise(p=.5, intensity=(0.1, 0.5), color_shift=(0.01, 0.05)),
    A.RandomBrightnessContrast(p=0.5, brightness_limit=(-0.2, 0.2), contrast_limit=(-0.2, 0.2), brightness_by_max=True),
    A.RandomGamma(p=.5, gamma_limit=(80, 120), eps=1e-07),
    A.MultiplicativeNoise(p=.5, multiplier=(0.9, 1.1), per_channel=True, elementwise=True),
    A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=10, val_shift_limit=10, p=.9),
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

    #TODO: likely need to accept here the checkpoint location
    classid = config["classid"] # --- this should result in a catastrophic failure if not provided
    tile_size = config["tile_size"] #probably this as well
    magnification = config["magnification"] #probably this as well
    actor_name = config["actor_name"]
    print (f"{actor_name=}")

    #TODO: all these from project settings
    batch_size_train=1
    batch_size_infer=1
    edge_weight=2
    num_workers=0 #set to num of CPUs? or...# of CPUs/ divided by # of classes or something...challenge - one started can't change

    dataset=TileDataset(classid, tile_size=tile_size, magnification=magnification,edge_weight=edge_weight, transforms=get_transforms(tile_size))

    dataloader = DataLoader(dataset, batch_size=batch_size_train, shuffle=False,num_workers=num_workers) #NOTE: for dataset of type iter - shuffle must == False

    model = smp.Unet(encoder_name="timm-mobilenetv3_small_100", encoder_weights="imagenet", in_channels=3, classes=1) #TODO: this should be a setting
    criterion = nn.BCEWithLogitsLoss(reduction='none')
    optimizer = optim.Adam(model.parameters(), lr=0.001) #TODO: this should be a setting
    
    #device = torch.device("cuda" if torch.cuda.is_available() else "cpu") #TODO: AJ - convert to ray dist train code
    if torch.cuda.is_available():
        localrank=ray.train.get_context().get_local_rank()
        device=torch.device('cuda',localrank)
    else:
        device= "cpu"
    
    model=ray.train.torch.prepare_model(model,device)
    model.train()


    running_loss = []
    last_save = 0
    niter_total = 0 
    #print ("pre actor get")
    myactor = ray.get_actor(actor_name)
    #print ("post actor get")
    while not ray.get(myactor.getCloseDown.remote()): 
        while tiles := getPendingInferenceTiles(classid,batch_size_infer): 
            #print (f"running inference on {len(tiles)}")
            run_inference(device, model, tiles)
            
        #print ("pretrain loop")
        if ray.get(myactor.getEnableTraining.remote()):
            #print ("in train loop")
            niter_total += 1
            images, masks, weights = next(iter(dataloader))
            #print ("post next iter")
            images = images.to(device)
            masks = masks.to(device)
            weights = weights.to(device)
            #print ("post copy ")
            optimizer.zero_grad()
            outputs = model(images)
            
            loss = criterion(outputs, masks.float())
            loss = (loss * (edge_weight ** weights).type_as(loss)).mean()
            
            positive_mask = (masks == 1).float()
            unlabeled_mask = (masks == 0).float()
            
            positive_loss = 1.0 * (loss * positive_mask).mean()
            unlabeled_loss = .1 * (loss * unlabeled_mask).mean()
            
            loss_total = positive_loss + unlabeled_loss
            loss_total.backward()
            
            optimizer.step()
            
            running_loss.append(loss_total.item())
            
            print ("losses:\t",loss_total,positive_mask.sum(),positive_loss,unlabeled_loss)
            
            last_save+=1
            if last_save>50:
                print (f"niter_total [{niter_total}], Loss: {sum(running_loss)/len(running_loss)}")
                running_loss=[]

                print ("saving!") #TODO: do we want to *always* override the last saved model , or do we want to instead only save if some type of loss threshold is met?
                                 #another potentially more interesting option is to do both, save on a regular basis (since if we things crash we can revert back othe nearest checkpoint\
                                 #but as well give the user in the front end a dropdown which enables them to select which model checkpoint they want to use? we had somethng similar in QAv1
                                 #that said, this is likely a more advanced features and not very "apple like" since it would require explaining to the user when/why/how they should use the different models
                                 #maybe suggest avoiduing for now --- lets just save the last one
                save_file(model.state_dict(), f"/tmp/model.safetensors") #TODO: needs to go somewhere reasonable maybe /projid/models/classid/ ? or something
                last_save = 0

            
    #print ("Exiting training!")