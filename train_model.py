import argparse
import json
import math
import os
import time
import re
import traceback
from datetime import datetime

import cv2
import numpy as np
import scipy.ndimage
import sys
import torch
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from albumentations import *
from albumentations.pytorch import ToTensor

import ttach as tta

from unet import UNet

from QA_utils import get_torch_device


# ---- estimate training time
def asMinutes(s):
    m = math.floor(s / 60)
    s -= m * 60
    return '%dm %ds' % (m, s)


def timeSince(since, percent):
    now = time.time()
    s = now - since
    es = s / (percent + .00001)
    rs = es - s
    return '%s (- %s)' % (asMinutes(s), asMinutes(rs))


# ----- setup dataset
class Dataset(object):
    def __init__(self, basedir, fname_list, transforms=None, edge_weight=False, batch_size=-1):
        self.basedir = basedir
        self.fnames = open(f"{basedir}/{fname_list}", "r").read().splitlines()

        self.transforms = transforms

        self.edge_weight = edge_weight

        # we will cache some masks in memory
        self.masks = {}

        self.batch_size = batch_size
        self.nitems = len(self.fnames) if self.batch_size == -1 else math.ceil(
            len(self.fnames) / self.batch_size) * self.batch_size

    def __getitem__(self, index):
        if self.batch_size == -1:
            fname = self.fnames[index]
        else:
            fname = self.fnames[index % len(self.fnames)]

        # load the roi image:
        img = cv2.cvtColor(cv2.imread(f"{self.basedir}/roi/{fname}"), cv2.COLOR_BGR2RGB)

        # extract the information from the filename pattern:
        match = re.search(r"(.*)_(\d+)_(\d+)_roi.png", fname)
        mask_name = match.group(1)
        x = int(match.group(2))
        y = int(match.group(3))
        h = img.shape[0]
        w = img.shape[1]

        # load the large mask for this roi and cache it:
        mask = self.masks.get(mask_name)
        if mask is None:
            mask_filename = f"{self.basedir}/mask/{mask_name}_mask.png"
            mask = cv2.imread(mask_filename)
            self.masks[mask_name] = mask

        # now extract the portion of the mask that this roi corresponds to:
        mask = mask[y:y + h, x:x + w, :]

        # convert it to the proper format:
        img_mask = np.zeros(mask[:, :, 0].shape, dtype=mask.dtype)
        img_mask[mask[:, :, 1] > 0] = 1  # [0,1,0] -- > positive class
        img_mask[(mask[:, :, 0] == 0) & (mask[:, :, 1] == 0)] = -1  # unknown class

        if (self.edge_weight):
            weight = scipy.ndimage.morphology.binary_dilation(img_mask, iterations=2) & ~img_mask
        else:
            weight = np.ones(img_mask.shape, dtype=mask.dtype)

        img_new = img
        mask_new = img_mask
        weight_new = weight

        if self.transforms:
            augmented = self.transforms(image=img, masks=[img_mask, weight])
            img_new = augmented['image']
            mask_new, weight_new = augmented['masks']

        return img_new, mask_new, weight_new

    def __len__(self):
        return self.nitems


try:
    print(f'USER: Starting Training DL model', flush=True)

    # ----- parse command line arguments
    parser = argparse.ArgumentParser(description='Train UNet')
    parser.add_argument('project_name', type=str)

    parser.add_argument('-p', '--patchsize', help="patchsize, default 256", default=256, type=int)
    parser.add_argument('-e', '--edgeweight', help="", default=2, type=float)
    parser.add_argument('-n', '--numepochs', help="", default=500, type=int)
    parser.add_argument('-s', '--numearlystopepochs',
                        help="Number of epochs to stop early if no validation progress has been made", default=-1,
                        type=int)
    parser.add_argument('-l', '--numminepochs',
                        help="Minimum number of epochs required before early stopping, default 300", default=300,
                        type=int)
    parser.add_argument('-b', '--batchsize', help="", default=16, type=int)
    parser.add_argument('-m', '--model', help="", default="./models/0/bestmodel.pth", type=str)
    parser.add_argument('-w', '--pclassweight',
                        help="Weight factor for the postivie class to help with balancing, default .5", default=.5,
                        type=float)
    parser.add_argument('-r', '--numworkers',
                        help="number of data loader workers to use, NOTE: will be set to 0 for windows", default=0,
                        type=int)
    parser.add_argument('-i', '--gpuid', help="GPU ID, set to -2 to use CPU", default=0, type=int)
    parser.add_argument('-o', '--outdir', help="", default="./", type=str)
    parser.add_argument('--fillbatch', action="store_true", help="Fill batch with repeats")

    # args = parser.parse_args(['-p256',"-w0.86", '-o./projects/ajtest/models/1/', '-m./projects/ajtest/models/0/best_model.pth', './projects/ajtest'])
    args = parser.parse_args()
    print(f"args: {args}")

    project_name = args.project_name
    patch_size = args.patchsize
    edge_weight = args.edgeweight
    batch_size = args.batchsize
    pclassweight = args.pclassweight
    num_epochs = args.numepochs
    num_epochs_earlystop = args.numearlystopepochs if args.numearlystopepochs > 0 else float("inf")
    num_min_epochs = args.numminepochs

    if os.name == "nt":
        numworkers = 0
    else:
        numworkers = args.numworkers if args.numworkers != -1 else os.cpu_count()

    newmodeldir = args.outdir
    iteration = newmodeldir.split("/")[4]
    # project_name has "projects/..." in the beginning
    projname = newmodeldir.split("/")[2]

    os.makedirs(newmodeldir, exist_ok=True)

    # ---- get model setup
    # retrieve device from config.ini file
    device = get_torch_device(args.gpuid)
    # map baseline model to desired device
    checkpoint = torch.load(args.model, map_location=lambda storage, loc: storage) #load checkpoint 
    # to CPU and then put to device; allows devices to differ between checkpoints 

    # +
    model = UNet(n_classes=checkpoint["n_classes"], in_channels=checkpoint["in_channels"],
                 padding=checkpoint["padding"], depth=checkpoint["depth"], wf=checkpoint["wf"],
                 up_mode=checkpoint["up_mode"], batch_norm=checkpoint["batch_norm"]).to(device)
    model.load_state_dict(checkpoint["model_dict"])
    print(f"total params: \t{sum([np.prod(p.size()) for p in model.parameters()])}", flush=True)

    n_classes = 2

    if checkpoint["n_classes"] != n_classes:
        model.last = torch.nn.Conv2d(4, n_classes, kernel_size=1)

    model.to(device)
    # -

    # from torchsummary import summary
    # summary(model.to(device), input_size=(3, 256, 256))

    # +
    # # freeze layers
    # for mod in model.down_path:
    #     for block in mod.block:
    # #        print(block, flush=True)
    #         block.requires_grad = False
    # # put to GPU
    # model = model.to(device)
    # -

    # +
    # https://github.com/albu/albumentations/blob/master/notebooks/migrating_from_torchvision_to_albumentations.ipynb
    transforms = Compose([
        RandomScale(scale_limit=0.1, p=.9),
        PadIfNeeded(min_height=patch_size, min_width=patch_size),
        VerticalFlip(p=.5),
        HorizontalFlip(p=.5),
        Blur(p=.5),
        # Downscale(p=.25, scale_min=0.64, scale_max=0.99),
        GaussNoise(p=.5, var_limit=(10.0, 50.0)),
        GridDistortion(p=.5, num_steps=5, distort_limit=(-0.3, 0.3),
                       border_mode=cv2.BORDER_REFLECT),
        ISONoise(p=.5, intensity=(0.1, 0.5), color_shift=(0.01, 0.05)),
        RandomBrightness(p=.5, limit=(-0.2, 0.2)),
        RandomContrast(p=.5, limit=(-0.2, 0.2)),
        RandomGamma(p=.5, gamma_limit=(80, 120), eps=1e-07),
        MultiplicativeNoise(p=.5, multiplier=(0.9, 1.1), per_channel=True, elementwise=True),
        HueSaturationValue(hue_shift_limit=20, sat_shift_limit=10, val_shift_limit=10, p=.9),
        Rotate(p=1, border_mode=cv2.BORDER_REFLECT),
        RandomCrop(patch_size, patch_size),
        ToTensor()
    ])

    transforms_test = Compose([
        PadIfNeeded(min_height=patch_size, min_width=patch_size),
        RandomCrop(patch_size, patch_size),
        ToTensor()
    ])
    # -

    # ------
    data_train = Dataset(basedir=project_name, fname_list="train_imgs.txt", transforms=transforms,
                         edge_weight=edge_weight, batch_size = batch_size if args.fillbatch else -1 )
    data_test = Dataset(basedir=project_name, fname_list="test_imgs.txt", transforms=transforms_test,
                        edge_weight=edge_weight, batch_size = batch_size if args.fillbatch else -1)

    # ------
    dataLoader = {}

    print('Loading data for training the model.', flush=True)
    dataLoader["train"] = DataLoader(data_train, batch_size=batch_size,
                                     shuffle=True, num_workers=numworkers, pin_memory=True)  # ,pin_memory=True)
    dataLoader["val"] = DataLoader(data_test, batch_size=batch_size,
                                   shuffle=False, num_workers=numworkers, pin_memory=True)  # ,pin_memory=True)

    # +
    # import matplotlib.pyplot as plt
    # img, mask, weight=data_train[0]
    # fig, ax = plt.subplots(1,4, figsize=(10,4))  # 1 row, 2 columns

    # #build output showing original patch  (after augmentation), class = 1 mask, weighting mask, overall mask (to see any ignored classes)
    # ax[0].imshow(np.moveaxis(img.numpy(),0,-1))
    # ax[1].imshow(mask==1)
    # ax[2].imshow(weight)
    # ax[3].imshow(mask)
    # plt.show()
    # -

    class_weight = torch.from_numpy(np.asarray([1 - pclassweight, pclassweight])).type('torch.FloatTensor').to(device)
    criterion = torch.nn.CrossEntropyLoss(ignore_index=-1, reduce=False, weight=class_weight)
    optim = torch.optim.Adam(model.parameters())

    best_epoch = -1
    best_loss_on_test = np.Infinity
    start_time = time.time()

    phases = ["train", "val"]
    validation_phases = ["train", "val"]
    writer = SummaryWriter(log_dir=f"{newmodeldir}/{datetime.now().strftime('%b%d_%H-%M-%S')}")
    for epoch in range(num_epochs):
        print(f'Starting epoch {epoch}/{num_epochs}.', flush=True)

        if (epoch > num_min_epochs and epoch - best_epoch > num_epochs_earlystop):
            print(
                f'USER: DL model training stopping due to lack of progress. Current Epoch:{epoch} Last Improvement: {best_epoch}',
                flush=True)
            break

        # all_loss = torch.zeros(0).to(device)
        all_acc = {key: 0 for key in phases}
        all_loss = {key: torch.zeros(0).to(device) for key in phases}
        cmatrix = {key: np.zeros((2, 2)) for key in phases}

        for phase in phases:
            if phase == 'train':
                model.train()  # Set model to training mode
            else:
                model.eval()  # Set model to evaluate mode
                tta_model = tta.SegmentationTTAWrapper(model, tta.aliases.d4_transform(), merge_mode='mean')

            with torch.set_grad_enabled(phase == 'train'):
                for X, y, y_weight in dataLoader[phase]:
                    X = X.to(device)  # [N, 1, H, W]
                    y = y.type('torch.LongTensor').to(device)  # [N, H, W] with class indices (0, 1)
                    y_weight = y_weight.to(device)

                    if phase == "val":
                        prediction = tta_model(X)  # [N, 2, H, W]
                    else:
                        prediction = model(X)  # [N, 2, H, W]

                    loss = criterion(prediction, y)
                    loss = (loss * (edge_weight ** y_weight).type_as(loss)).mean()

                    if phase == "train":
                        optim.zero_grad()
                        loss.backward()
                        optim.step()
                        train_loss = loss

                    all_loss[phase] = torch.cat((all_loss[phase], loss.detach().view(1, -1)))

                    if phase in validation_phases:  # if this phase is part of validation, compute confusion matrix
                        p = prediction[:, :, :, :].detach().cpu().numpy()
                        cpredflat = np.argmax(p, axis=1).flatten()
                        yflat = y.cpu().numpy().flatten()
                        confusion_matrix = scipy.sparse.coo_matrix(
                            (np.ones(yflat.shape[0], dtype=np.int64), (yflat, cpredflat)),
                            shape=(n_classes, n_classes), dtype=np.int64, ).toarray()

                        cmatrix[phase] = cmatrix[
                                             phase] + confusion_matrix  # confusion_matrix(yflat, cpredflat, labels=range(2))

            all_acc[phase] = (cmatrix[phase] / cmatrix[phase].sum()).trace()
            all_loss[phase] = all_loss[phase].cpu().numpy().mean()

            # save metrics to tensorboard
            writer.add_scalar(f'{phase}/loss', all_loss[phase], epoch)
            if phase in validation_phases:
                writer.add_scalar(f'{phase}/acc', all_acc[phase], epoch)
                writer.add_scalar(f'{phase}/TN', cmatrix[phase][0, 0], epoch)
                writer.add_scalar(f'{phase}/TP', cmatrix[phase][1, 1], epoch)
                writer.add_scalar(f'{phase}/FP', cmatrix[phase][0, 1], epoch)
                writer.add_scalar(f'{phase}/FN', cmatrix[phase][1, 0], epoch)
                writer.add_scalar(f'{phase}/TNR', cmatrix[phase][0, 0] / (cmatrix[phase][0, 0] + cmatrix[phase][0, 1]),
                                  epoch)
                writer.add_scalar(f'{phase}/TPR', cmatrix[phase][1, 1] / (cmatrix[phase][1, 1] + cmatrix[phase][1, 0]),
                                  epoch)

        print(f'PROGRESS: {epoch + 1}/{num_epochs} | {timeSince(start_time, (epoch + 1) / num_epochs)} | {all_loss["train"]} | {all_loss["val"]}', flush=True)

        print('%s ([%d/%d] %d%%), train loss: %.4f test loss: %.4f' % (timeSince(start_time, (epoch + 1) / num_epochs),
                                                                       epoch + 1, num_epochs,
                                                                       (epoch + 1) / num_epochs * 100,
                                                                       all_loss["train"],
                                                                       all_loss["val"]), end="", flush=True)

        # --- done with epoch, is model better than last?
        if all_loss["val"] < best_loss_on_test:
            best_loss_on_test = all_loss["val"]
            best_epoch = epoch
            print("  **", flush=True)

            state = {'epoch': epoch + 1,
                     'model_dict': model.state_dict(),
                     'optim_dict': optim.state_dict(),
                     'best_loss_on_test': all_loss,
                     'n_classes': 2,
                     'in_channels': checkpoint["in_channels"],
                     'padding': checkpoint["padding"],
                     'depth': checkpoint["depth"],
                     'wf': checkpoint["wf"],
                     'up_mode': checkpoint["up_mode"], 'batch_norm': checkpoint["batch_norm"]}

            torch.save(state, f"{newmodeldir}/best_model.pth")
        else:
            print("", flush=True)

    print(f'USER: Done Training of DL model', flush=True)

    print(f"RETVAL: {json.dumps({'project_name': projname, 'iteration': iteration})}", flush=True)
except:
    track = traceback.format_exc()
    track = track.replace("\n", "\t")
    print(f"ERROR: {track}", flush=True)
    sys.exit(1)

# checkpoint = torch.load(f"{newmodeldir}/best_model.pth", map_location=lambda storage,
# loc: storage)  # load checkpoint to CPU and then put to device https://discuss.pytorch.org/t/saving-and-loading-torch-models-on-2-machines-with-different-number-of-gpu-devices/6666
# model = UNet(n_classes=checkpoint["n_classes"], in_channels=checkpoint["in_channels"],
# padding=checkpoint["padding"], depth=checkpoint["depth"], wf=checkpoint["wf"],
# up_mode=checkpoint["up_mode"], batch_norm=checkpoint["batch_norm"]).to(device)
# model.load_state_dict(checkpoint["model_dict"])
# model.eval()

# # +
# import  matplotlib.pyplot as plt
# img, mask, weight=data_train[0]

# fig, ax = plt.subplots(1,4, figsize=(10,4))  # 1 row, 2 columns

# #build output showing original patch  (after augmentation), class = 1 mask, weighting mask, overall mask (to see any ignored classes)
# ax[0].imshow(np.moveaxis(img.numpy(),0,-1))
# ax[1].imshow(mask==1)
# ax[2].imshow(weight)
# ax[3].imshow(mask)
# plt.show()


# # -

# def getImage(X,i):
# return np.moveaxis(X[i,:,:,:].detach().cpu().numpy(),0,-1)


# class LayerActivations():
# features=None
# def __init__(self,layer):
# self.hook = layer.register_forward_hook(self.hook_fn)
# def hook_fn(self,module,input,output):
# self.features = output
# def remove(self):
# self.hook.remove()

# dr=LayerActivations(model.up_path[-1].conv_block.block[-1])

# # +
# tta_model = tta.SegmentationTTAWrapper(model, tta.aliases.d4_transform(), merge_mode='max')

# #visualize a single example to verify that it is correct
# for ii,(img, mask, weight) in enumerate(data_test):
# #output=model(img[None,::].to(device))
# #output=tta_model(img[None,::].to(device))
# output=model(img[None,::].to(device))
# output=output.detach().squeeze().cpu().numpy()
# output=np.moveaxis(output,0,-1)

# fig, ax = plt.subplots(1,5, figsize=(20,10))  # 1 row, 2 columns

# io=np.moveaxis(img.numpy(),0,-1)
# binout=output.argmax(axis=2)

# ax[0].imshow(output[:,:,1])
# ax[1].imshow(binout)
# ax[2].imshow(io)
# ax[3].imshow(mask)
# ax[4].imshow(io)
# ax[4].imshow(binout,alpha=.7)

# plt.show()
# if(ii>10):
# break
# # -
# chan8=getImage(dr.features,0)


# import umap
# embedding = umap.UMAP(n_components=3).fit_transform(chan8.reshape(-1,8))

# chan3=embedding.reshape(256,256,3)

# plt.imshow(chan3)

# # +
# fig, ax = plt.subplots(1,2, figsize=(20,10))  # 1 row, 2 columns

# ax[1].imshow(io)
# ax[1].imshow(chan3,alpha=.1)
# # -
