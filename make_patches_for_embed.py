# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.4'
#       jupytext_version: 1.1.7
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


try:
    # +
    parser = argparse.ArgumentParser(description='Convert image and mask into non-overlapping patches')
    parser.add_argument('-p', '--patchsize', help="Patchsize, default 256", default=256, type=int)
    parser.add_argument('-o', '--outdir', help="Target output directory", default="./", type=str)
    parser.add_argument('-m', '--mask',  action="store_true", help="Treat files like _mask.png as masks")
    parser.add_argument('-b', '--bgremoved',  action="store_true", help="Don't save patches which are considered background, useful for TMAs")
    parser.add_argument('input_pattern',
                            help="Input filename pattern (try: *.png), or txt  file containing list of files",
                            nargs="*")

    #todo: add in random sampling

    #args = parser.parse_args(["-m","-opatches","*.png"])
    args = parser.parse_args()
    print(f"args: {args}")
    print(f"USER: Starting make patches for {args.outdir}", flush=True)

    # +
    patch_size = args.patchsize
    outdir = args.outdir + os.sep if len(args.outdir) > 0 else ""  # if the user supplied a different basepath, make sure it ends with an os.sep
    domask  = args.mask

    if not os.path.isdir(f"{outdir}"):
        os.mkdir(f"{outdir}")

    if domask and not os.path.isdir(f"{outdir}/mask"):
        os.mkdir(f"{outdir}/mask")


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
    print("--------------------------", flush=True)
    print(fnames)
    nimages=len(fnames)
    print(f"USER: Identified {nimages} images", flush=True)

    for ii,fname in enumerate(fnames):
        print(fname, flush=True)
        print(f"PROGRESS: {ii+1}/{nimages}", flush=True)
        fnamebase = os.path.splitext(os.path.basename(fname))[0]

        if(domask and fname.find("_mask.png")>0):
            print(f"Treating {fname} as mask")
            ismask=True
            fnamebase=fnamebase.replace("_mask","")

        else:
            ismask=False

        image = cv2.imread(fname)  #NOTE: this image is in BGR not RGB format
        if(ismask):
            image=np.dstack([(image[:,:,0]==0)*255,
                             (image[:,:,0]>0)*255,
                             np.ones(image.shape[0:2])*255])


        idxs=np.asarray(range(image.shape[0]*image.shape[1])).reshape(image.shape[0:2])

        patch_out = sklearn.feature_extraction.image.extract_patches(image,(patch_size,patch_size,3),patch_size)
        patch_out = patch_out.reshape(-1,patch_size,patch_size,3)


        idx_out = sklearn.feature_extraction.image.extract_patches(idxs,(patch_size,patch_size),patch_size)
        idx_out=idx_out[:,:,0,0]
        idx_out=idx_out.reshape(-1)
        rs,cs=np.unravel_index(idx_out,idxs.shape)

        for r,c,patch in zip(rs,cs,patch_out):

            gpatch = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
            if(args.bgremoved and gpatch.mean()>240):
                continue

            cv2.imwrite(f"{outdir}/{'mask' if ismask else ''}/{fnamebase}_{c}_{r}{'_mask' if ismask else ''}.png",patch) #writing in BGR not RGB format...as intended
    # -
    print(f"USER: Done making patches for {outdir}!", flush=True)

    number_of_patches = len(glob.glob(os.path.join(outdir,"*.png")))
    print(f"USER: Total number of patches = {number_of_patches}.", flush=True)

    print(f"RETVAL: {json.dumps({'image_list': fnames})}", flush=True)


except:
    track = traceback.format_exc()
    track = track.replace("\n","\t")
    print(f"ERROR: {track}", flush=True)
    sys.exit(1)
