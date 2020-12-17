# ---
# jupyter:
#   jupytext:
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

import os
import cv2
import glob
import argparse
import traceback
import sys
import json
import numpy as np
import sklearn.feature_extraction.image
from pathlib import Path
from tqdm.autonotebook import tqdm


# +
os.environ['PATH'] = 'C:\\research\\openslide\\bin' + ';' + os.environ['PATH'] #can either specify openslide bin path in PATH, or add it dynamically

import openslide


# +
parser = argparse.ArgumentParser(description='Convert image and mask into non-overlapping patches')
parser.add_argument('-p', '--patchsize', help="Patchsize, default 256", default=256, type=int)
parser.add_argument('-l', '--openslidelevel', help="openslide level to use", default=0, type=int)
parser.add_argument('-o', '--outdir', help="Target output directory", default="./", type=str)
parser.add_argument('-b', '--bgremoved',  action="store_true", help="Don't save patches which are considered background, useful for TMAs")
parser.add_argument('input_pattern', help="Input filename pattern (try: *.png), or txt  file containing list of files", nargs="*")

#args = parser.parse_args(["-l1","-b","-p2000",r"D:\research\chuv_melanoma\Patient 1\M160902-HE.svs"])
args = parser.parse_args()
print(f"args: {args}")
print(f"USER: Starting make patches for {args.outdir}", flush=True)


# +
patch_size = args.patchsize
outdir = args.outdir + os.sep if len(args.outdir) > 0 else ""  # if the user supplied a different basepath, make sure it ends with an os.sep
level = args.openslidelevel

if not os.path.isdir(f"{outdir}"):
    os.mkdir(f"{outdir}")



# +
fnames = []

if len(args.input_pattern) > 1:  # bash has sent us a list of files
    fnames = args.input_pattern
elif args.input_pattern[0].endswith("txt"):  # user sent us an input file
    with open(args.input_pattern[0], 'r') as f:
        for line in f:
            fnames.append(line.strip())
else:  # user sent us a wildcard, need to use glob to find files
    fnames = glob.glob(args.input_pattern[0])


# +
print(f"Identified {len(fnames)} image(s)")

for ii,fname in tqdm(enumerate(fnames),leave=False):
    fnamebase=Path(os.path.basename(fname)).stem
    
    print(f"{fname}")
    fnamebase = os.path.splitext(os.path.basename(fname))[0]

    osh  = openslide.OpenSlide(fname)
    nrow,ncol = osh.level_dimensions[0]

    for y in tqdm(range(0,osh.level_dimensions[0][1],round(patch_size * osh.level_downsamples[level])), desc="outer" , leave=False):
        for x in tqdm(range(0,osh.level_dimensions[0][0],round(patch_size * osh.level_downsamples[level])), desc=f"innter {y}", leave=False):
    
            
            patch  = np.asarray(osh.read_region((x, y), level, (patch_size,patch_size)))[:,:,0:3] #trim alpha

            if(args.bgremoved):
                gpatchmean = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY).mean()
                if(gpatchmean>200 or gpatchmean<50):
                    continue

        
            patch=cv2.cvtColor(patch,cv2.COLOR_RGB2BGR)
            cv2.imwrite(f"{fnamebase}_{level}_{y}_{x}.png",patch)

    osh.close()


print(f"Done making patches!")


# -


