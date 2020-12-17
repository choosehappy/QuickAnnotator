# ---
# jupyter:
#   jupytext:
#     cell_metadata_json: true
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.4.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# +
# https://github.com/jvanvugt/pytorch-unet

print('STARTING AUTOENCODER TRAINING SCRIPT', flush=True)

import argparse
import os
import traceback
import sys

import torch
from torch import nn
from torch.utils.data import DataLoader

from albumentations import *
from albumentations.pytorch import ToTensor

from unet import UNet

import cv2

import numpy as np
import glob

from tensorboardX import SummaryWriter
from datetime import datetime

import time
import math

from QA_utils import get_torch_device


# -

def asMinutes(s):
    m = math.floor(s / 60)
    s -= m * 60
    return '%dm %ds' % (m, s)
def timeSince(since, percent):
    now = time.time()
    s = now - since
    es = s / (percent+.00001)
    rs = es - s
    return '%s (- %s)' % (asMinutes(s), asMinutes(rs))


class LayerActivations():
    features=None
    def __init__(self,layer):
        self.hook = layer.register_forward_hook(self.hook_fn)
    def hook_fn(self,module,input,output):
        self.features = output
    def remove(self):
        self.hook.remove()


class Dataset(object):
    def __init__(self, fnames,transform=None, maximgs=-1):
        self.fnames=fnames
        self.transform=transform
        self.maximgs = min(maximgs,len(self.fnames))
        
    def __getitem__(self, index):
        
        index = index if self.maximgs==-1 else np.random.randint(0,self.maximgs) 
        
        fname=self.fnames[index]
        image = cv2.cvtColor(cv2.imread(fname), cv2.COLOR_BGR2RGB)
        patch = image
        if self.transform is not None:
            patch1 = self.transform(image=image)['image']
            patch2 = self.transform(image=image)['image']

        return patch1,patch2, image
    
    def __len__(self):
        return len(self.fnames) if self.maximgs==-1 else self.maximgs


# +
try:
    parser = argparse.ArgumentParser(description='Train AutoEncoder')
    parser.add_argument('input_pattern', type=str)

    parser.add_argument('-p', '--patchsize', help="patchsize, default 256", default=256, type=int)
    parser.add_argument('-n', '--numepochs', help="", default=150, type=int)
    parser.add_argument('-s', '--numearlystopepochs', help="Number of epochs to stop early if no validation progress has been made", default=-1, type=int)
    parser.add_argument('-l', '--numminepochs',help="Minimum number of epochs required before early stopping, default 300", default=300, type=int)
    parser.add_argument('-m', '--numimgs', help="Number of images to use per epoch, default is-1, implying all", default=-1, type=int)
    parser.add_argument('-b', '--batchsize', help="", default=8, type=int)
    parser.add_argument('-r', '--numworkers', help="number of data loader workers to use, NOTE: must be 0 for windows", default=0, type=int)
    parser.add_argument('-i', '--gpuid', help="GPU ID, set to -2 to use CPU", default=0, type=int)
    parser.add_argument('-o', '--outdir', help="", default="./", type=str)

    #args = parser.parse_args(['-o./projects/ajtest/models/0', './projects/ajtest/patches/*.png'])
    #args = parser.parse_args(['-n100', '-m-1', '-b32', '-o./projects/ajtest/models/0', './projects/ajtest/patches/*.png'])
    print("Parsing arguments:", flush=True)
    args = parser.parse_args()
    print(f"args: {args}")


    print(f"Making directory {args.outdir}:", flush=True)
    os.makedirs(args.outdir, exist_ok=True)
    print(f'USER: Starting Training of base model', flush=True)

    input_pattern = args.input_pattern

    patch_size = args.patchsize
    num_imgs = args.numimgs
    batch_size = args.batchsize
    num_epochs = args.numepochs
    num_epochs_earlystop = args.numearlystopepochs if args.numearlystopepochs > 0 else float("inf")
    num_min_epochs = args.numminepochs

    if os.name =="nt":
        numworkers = 0
    else:
        numworkers = args.numworkers if args.numworkers!=-1 else os.cpu_count()


    n_classes= 3
    in_channels= 3 
    padding= True
    depth= 5
    wf= 2
    up_mode= 'upsample' 
    batch_norm = True


    print("Getting torch device:", flush=True)
    device = get_torch_device()

    print("Initializing model:", flush=True)
    model = UNet(n_classes=n_classes, in_channels=in_channels, padding=padding,
                        depth=depth,wf=wf, up_mode=up_mode, batch_norm=batch_norm , concat=True).to(device)

    print(f"total params: \t{sum([np.prod(p.size()) for p in model.parameters()])}", flush=True)


#    from torchsummary import summary
#    summary(model,(3,256,256))


    dr=LayerActivations(model.down_path[-1].block[5])


    # +
    img_transform = Compose([
            RandomScale(scale_limit=0.1,p=.9),
            PadIfNeeded(min_height=patch_size,min_width=patch_size),        
            VerticalFlip(p=.5),
            HorizontalFlip(p=.5),
            Blur(p=.5),
            #Downscale(p=.25, scale_min=0.64, scale_max=0.99),
            GaussNoise(p=.5, var_limit=(10.0, 50.0)),
            GridDistortion(p=.5, num_steps=5, distort_limit=(-0.3, 0.3), 
                           border_mode=cv2.BORDER_REFLECT),
            ISONoise(p=.5, intensity=(0.1, 0.5), color_shift=(0.01, 0.05)),
            RandomBrightness(p=.5, limit=(-0.2, 0.2)),
            RandomContrast(p=.5, limit=(-0.2, 0.2)),
            RandomGamma(p=.5, gamma_limit=(80, 120), eps=1e-07),
            MultiplicativeNoise(p=.5, multiplier=(0.9, 1.1), per_channel=True, elementwise=True),
            HueSaturationValue(hue_shift_limit=20,sat_shift_limit=10,val_shift_limit=10,p=.9),
            Rotate(p=1, border_mode=cv2.BORDER_REFLECT),
            RandomCrop(patch_size,patch_size),
            ToTensor()
        ])

    print(f"Getting training data for pattern {input_pattern}:", flush=True)
    data_train=Dataset(glob.glob(input_pattern), transform=img_transform, maximgs=num_imgs) #img_transform)

    print(f"Creating loader for training data:", flush=True)
    data_train_loader = DataLoader(data_train, batch_size=batch_size, 
                                   shuffle=True, num_workers=numworkers, pin_memory=True)

    # +
    # (patch, img)=data_train[2]
    # fig, ax = plt.subplots(1,2, figsize=(10,4))  # 1 row, 2 columns

    # #build output showing original patch  (after augmentation), class = 1 mask, weighting mask, overall mask (to see any ignored classes)
    # ax[0].imshow(np.moveaxis(patch.numpy(),0,-1))
    # ax[1].imshow(img)
    # -


    optim = torch.optim.Adam(model.parameters(),lr=.1)


    best_loss = np.infty

    color_trans = Compose([
           HueSaturationValue(hue_shift_limit=50,sat_shift_limit=0,val_shift_limit=0,p=1),
           ToTensor()
        ])


    # +
    start_time = time.time()
    writer = SummaryWriter(logdir=f"{args.outdir}/{datetime.now().strftime('%b%d_%H-%M-%S')}") 
    criterion = nn.MSELoss() 
    best_loss = np.infty
    best_epoch = -1


    for epoch in range(num_epochs):
        if(epoch> num_min_epochs  and epoch-best_epoch > num_epochs_earlystop):
            print(f'USER: DL model training stopping due to lack of progress. Current Epoch:{epoch} Last Improvement: {best_epoch}', flush=True)
            break
        all_loss = torch.zeros(0).to(device)
        for X1, X2, X_orig  in data_train_loader:
            X = torch.cat((X1, X2), 0)
            X = X.to(device)  
            
            halfX=int(X.shape[0]/2)
            
            prediction = model(X)  # [N, 2, H, W]
            Xfeatures=dr.features
            
            loss1 = criterion(prediction, X)
            loss2 = criterion(Xfeatures[0:halfX,::], Xfeatures[halfX:,::])
            
            loss=loss1+loss2

                    
            optim.zero_grad()
            loss.backward()
            optim.step()

            all_loss = torch.cat((all_loss, loss.detach().view(1, -1)))

        writer.add_scalar(f'train/loss', loss, epoch)

        print(f'PROGRESS: {epoch+1}/{num_epochs} | {timeSince(start_time, (epoch+1) / num_epochs)} | {loss.data}', flush=True)

        print('%s ([%d/%d] %d%%),total loss: %.4f \t loss1: %.4f \t loss2: %.4f ' % (timeSince(start_time, (epoch+1) / num_epochs),
                                                 epoch+1, num_epochs ,(epoch+1) / num_epochs * 100, loss.data,loss1.data,loss2.data),end="", flush=True)


        all_loss = all_loss.cpu().numpy().mean()
        if all_loss < best_loss:
            best_loss = all_loss
            best_epoch = epoch
            print("  **", flush=True)

            state = {'epoch': epoch + 1,
                     'model_dict': model.state_dict(),
                     'optim_dict': optim.state_dict(),
                     'best_loss_on_test': all_loss,
                     'n_classes': n_classes,
                     'in_channels': in_channels,
                     'padding': padding,
                     'depth': depth,
                     'wf': wf,
                     'up_mode': up_mode, 'batch_norm': batch_norm}

            torch.save(state, f"{args.outdir}/best_model.pth")
        else:
            print("", flush=True)

    print(f'USER: Training of base model complete!', flush=True)

    projname=args.outdir.split("/")[2]
    print(f"RETVAL: {projname}", flush=True)

except:
    track = traceback.format_exc()
    track = track.replace("\n","\t")
    print(f"ERROR: {track}", flush=True)
    sys.exit(1)

# +
# import  matplotlib.pyplot as plt
# img, imorig = data_train[2]



# output=model(img[None,::].to(device))
# output=output.detach().squeeze().cpu().numpy()
# output=np.moveaxis(output,0,-1) 
# output.shape


# fig, ax = plt.subplots(1,2, figsize=(10,4))  # 1 row, 2 columns

# #build output showing original patch  (after augmentation), class = 1 mask, weighting mask, overall mask (to see any ignored classes)
# ax[0].imshow(np.moveaxis(img.numpy(),0,-1))
# ax[1].imshow(output)

# plt.show()
# # -





# X.shape





# def getImage(X,i):
    # return np.moveaxis(X[i,:,:,:].detach().cpu().numpy(),0,-1)


# plt.imshow(getImage(X,3))

# plt.imshow(Xfeatures[3,3,:,:].squeeze().detach().cpu().numpy())

# plt.imshow(Xmodfeatures[1,7,:,:].squeeze().detach().cpu().numpy())



# #---- rubbish below?


# # +

# fig, ax = plt.subplots(1,2, figsize=(10,4))  # 1 row, 2 columns

# #build output showing original patch  (after augmentation), class = 1 mask, weighting mask, overall mask (to see any ignored classes)
# ax[0].imshow(xorig)
# ax[1].imshow(np.moveaxis(x.cpu().numpy(),0,-1))


# # +
# Xmod=np.zeros(X.shape)
# for ii,x in enumerate(X):
    # #print(x.shape)
    # xorig = np.moveaxis(x.cpu().numpy(),0,-1)*255
    # xorig = xorig.astype(np.uint8)
    # x = color_trans(image=xorig)['image']
    # Xmod[ii,::]=x

# dummy = model(torch.from_numpy(Xmod).type('torch.FloatTensor').to(device))  # [N, 2, H, W]
# Xmodfeatures=dr.features
# # -


# data_train=Dataset(glob.glob('./projects/glom/patches/*.png'), transform=img_transform) #img_transform)
# data_train_loader = DataLoader(data_train, batch_size=batch_size, 
                               # shuffle=True, num_workers=0, pin_memory=True) #,pin_memory=True)
# [img,img2]=data_train[3]
# # +
# # #%%timeit
# output=model(img[None,::].to(device))
# output=output.detach().squeeze().cpu().numpy()
# output=np.moveaxis(output,0,-1) 
# output.shape

# fig, ax = plt.subplots(1,2, figsize=(10,4))  # 1 row, 2 columns

# ax[0].imshow(output)
# ax[1].imshow(np.moveaxis(img.numpy(),0,-1))
# # -

