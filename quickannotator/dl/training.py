import segmentation_models_pytorch as smp
import torch
from torch.utils.data import DataLoader
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm

from quickannotator.dl.inference import run_inference, getTileStatus
from .dataset import TileDataset
import io
import albumentations as A
from albumentations.pytorch import ToTensorV2
import cv2

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



def train_model(config):
    is_train = config.get("is_train",True) # else True #default to training
    allow_pred = config.get("allow_pred",True) #default to enable predts
    classid = config["classid"] # --- this should result in a catastrophic failure if not provided
    tile_size = config["tile_size"] #probably this as well
    # from project settings
    num_epochs=10 # probably needs to be huge, or potentially even Inf
    batch_size=1
    edge_weight=2

    dataset=TileDataset(classid, edge_weight=edge_weight, transforms=get_transforms(tile_size))

    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    model = smp.Unet(encoder_name="timm-mobilenetv3_small_100", encoder_weights="imagenet", in_channels=3, classes=1)
    criterion = nn.BCEWithLogitsLoss(reduction='none')
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = model.to(device)


    if tiles := getTileStatus(classid): #to be moved into for loop
        print(f"running inference on {len(tiles)}")
        run_inference(model, tiles, device)

    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        for images, masks, weights in tqdm(dataloader):


            if tiles := getTileStatus(classid):
                print(f"running inference on {len(tiles)}")
                run_inference(model, tiles, device)

            images = images.to(device)
            masks = masks.to(device)
            weights = weights.to(device)
            
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
            
            running_loss += loss_total.item()
            
            print("losses:\t",loss_total,positive_mask.sum(),positive_loss,unlabeled_loss)

        print(f"Epoch [{epoch+1}/{num_epochs}], Loss: {running_loss/len(dataloader)}")
    print("Training complete")