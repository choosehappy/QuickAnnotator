# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.3.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# +
# https://github.com/jvanvugt/pytorch-unet
import json
import warnings

warnings.filterwarnings("ignore")

import argparse
import traceback
from collections import OrderedDict
import torch
from torch import nn
from torch.utils.data import DataLoader

from albumentations import *
from albumentations.pytorch import ToTensor


from unet import UNet
import cv2

import numpy as np
import glob

import random, sys
import os

import umap


from QA_utils import get_torch_device

# +

class Dataset(object):
    def __init__(self, fnames,patch_size,transform=None):
        print('Initializing dataset:')
        self.fnames=fnames
        self.patch_size=patch_size
        self.transform=transform
    def __getitem__(self, index):
        fname=self.fnames[index]
        image = cv2.cvtColor(cv2.imread(fname), cv2.COLOR_BGR2RGB)
        patch = image

        if self.transform is not None:
            patch = self.transform(image=image)['image']

            #have fixed using set seed of random package
        return patch, fname
    
    def __len__(self):
        return len(self.fnames)


try:
    print("USER: Starting to embed patches")
    parser = argparse.ArgumentParser(description='make embedding using umap')
    parser.add_argument('project_name', type=str)

    parser.add_argument('-p', '--patchsize', help="patchsize, default 256", default=256, type=int)
    parser.add_argument('-b', '--batchsize', help="", default=32, type=int)
    parser.add_argument('-m', '--numimgs', help="Number of images to in embedding, default is-1, implying all", default=-1, type=int)
    parser.add_argument('-i', '--gpuid', help="GPU ID, set to -2 to use CPU", default=0, type=int)
    parser.add_argument('-o', '--outdir', help="", default="./", type=str)

    args = parser.parse_args()
    print(f"args: {args}")

    project_name = args.project_name
    patch_size = args.patchsize
    batch_size = args.batchsize
    num_imgs = args.numimgs
    modelid = args.outdir.split("/")[4]


    model_name = f"{args.outdir}/best_model.pth"
    if(not os.path.exists(model_name)):
        print(f"Can't find model {model_name}, exiting")
        sys.exit()
    # -

    # get the device to run deep learning
    print('Getting device:', flush=True)
    device = get_torch_device(args.gpuid)

    print('Loading checkpoint:', flush=True)
    checkpoint = torch.load(model_name, map_location=lambda storage, loc: storage) #load checkpoint to CPU and then put to device https://discuss.pytorch.org/t/saving-and-loading-torch-models-on-2-machines-with-different-number-of-gpu-devices/6666

    print('Creating model:', flush=True)
    model = UNet(n_classes=checkpoint["n_classes"], in_channels=checkpoint["in_channels"],
                 padding=checkpoint["padding"], depth=checkpoint["depth"], wf=checkpoint["wf"],
                 up_mode=checkpoint["up_mode"], batch_norm=checkpoint["batch_norm"]).to(device)
    model.load_state_dict(checkpoint["model_dict"])

    print(f"total params: \t{sum([np.prod(p.size()) for p in model.parameters()])}")


    # -

    # +
    rois=glob.glob(f"./projects/{project_name}/roi/*.png")
    patches=glob.glob(f"./projects/{project_name}/patches/*.png")

    #if we don't want entire list, subset it randomly. note. we always take all rois
    if (num_imgs !=-1):
        maximgs= min(num_imgs,len(patches))
        patches=random.sample(patches,maximgs)

    patches=sorted(patches,key=os.path.getctime) # needed for colors in the front end to appear consistent

    # +
    img_transform = Compose([
           RandomCrop(height=patch_size, width=patch_size, always_apply=True), 
           PadIfNeeded(min_height=patch_size,min_width=patch_size),
           ToTensor()
        ])

    data_train=Dataset(patches+rois, patch_size=patch_size,transform=img_transform) #img_transform)
    data_train_loader = DataLoader(data_train, batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=True)
    # -

    model.up_path=nn.ModuleList()
    model.last=nn.Sequential()

    # +
    all_imgs=[]
    #all_preds=[]
    all_preds_full=[]
    all_fnames=[]
    niter=len(data_train_loader)
    for ii, (X, fname) in enumerate(data_train_loader):
        print(f"PROGRESS: {ii+1}/{niter} | | Feature Gen")
        print('Sending data to device:')
        X = X.to(device)
        prediction = model(X)
        pred=prediction.detach().cpu().numpy()
        all_preds_full.append(pred)

    #    pred=pred.reshape(X.shape[0],-1)
    #    all_preds.append(pred)

        all_fnames.extend(fname)

    #all_preds=np.vstack(all_preds)
    all_preds_full=np.vstack(all_preds_full)
    # -

    all_preds_full=all_preds_full.reshape(all_preds_full.shape[0],all_preds_full.shape[1],-1)

    # +
    features_hists=[]
    for i in range(all_preds_full.shape[1]):
        print(f"PROGRESS: {i+1}/{all_preds_full.shape[1]} | | Histogram Gen")
        print(f'Processing histogram {i}:', flush=True)
        filt=all_preds_full[:,i,:]
        mean=filt.mean()
        std=filt.std()
        hists=np.apply_along_axis(lambda a: np.histogram(a, bins=10, range=(mean-std,mean+std))[0], 1, filt)
        features_hists.append(hists)

    features_hists=np.hstack(features_hists)

    # -

    print('Fitting umap to histogram:', flush=True)
    embedding = umap.UMAP(n_neighbors=100,min_dist=0.0).fit_transform(features_hists)

    # +
    all_fnames_base=[]

    for fname in all_fnames:
        fname=os.path.basename(fname).replace("_roi.png",".png")
        fname= fname[0:fname[0:fname.rfind("_",)].rfind("_")]
        all_fnames_base.append(fname)

    id_s = {c: i for i, c in enumerate(OrderedDict.fromkeys(all_fnames_base))}
    li = [id_s[c] for c in all_fnames_base]
    # -

    print('Saving to embedding.csv:')
    f = open(f"{args.outdir}/embedding.csv", "w")
    f.write("#filename,group,x,y\n")
    for fname,group,emb in zip(all_fnames,li,embedding):
        f.write(f"{fname},{group},{emb[0]},{emb[1]}\n")
    f.close()

    print("USER: Done embedding patches", flush=True)

    print(f"RETVAL: {json.dumps({'project_name': project_name,'modelid':modelid})}", flush=True)

except:
    track = traceback.format_exc()
    track = track.replace("\n","\t")
    print(f"ERROR: {track}", flush=True)
    sys.exit(1)
