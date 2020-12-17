import argparse
import glob
import os
import sys
import traceback
import json


import cv2
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.color import rgb2gray
from skimage.filters import rank
from skimage.morphology import disk
from skimage.restoration import denoise_tv_chambolle
from skimage.segmentation import watershed, find_boundaries

try:
    # ----- parse command line arguments
    print("USER: Generating Superpixel output", flush=True)
    parser = argparse.ArgumentParser(description='Make superpixel and boundary output')
    parser.add_argument('input_pattern',
                        help="input filename pattern. try: *.png, or tsv file containing list of files to analyze",
                        nargs="*")
    parser.add_argument('-m', '--model', help="DL model location, default None", default=None, type=str)
    parser.add_argument('-s', '--superdir', help="output dir for superpixel, default ./output/", default="./output/", type=str)
    parser.add_argument('-o', '--boundarydir', help="output dir for superpixel boundary, default ./output/", default="./output/", type=str)
    parser.add_argument('-b', '--basepath', help="base path to add to file names, helps when producing data using tsv file as input", default="", type=str)

    parser.add_argument('-f', '--force', help="force regeneration of output even if it exists", default=False,
                        action="store_true")

    args = parser.parse_known_args()[0]
    print(f"args: {args}")

    if not (args.input_pattern):
        parser.error('No images selected with input pattern')

    superoutdir = args.superdir
    boutdir = args.boundarydir

    if not os.path.exists(superoutdir):
        os.makedirs(superoutdir)

    if not os.path.exists(boutdir):
        os.makedirs(boutdir)

    files = []
    basepath = args.basepath  #
    basepath = basepath + os.sep if len(
        basepath) > 0 else ""  # if the user supplied a different basepath, make sure it ends with an os.sep

    if len(args.input_pattern) > 1:  # bash has sent us a list of files
        files = args.input_pattern
    elif args.input_pattern[0].endswith("tsv"):  # user sent us an input file
        # load first column here and store into files
        with open(args.input_pattern[0], 'r') as f:
            for line in f:
                if line[0] == "#":
                    continue
                files.append(basepath + line.strip().split("\t")[0])
    else:  # user sent us a wildcard, need to use glob to find files
        files = glob.glob(args.basepath + args.input_pattern[0])

    # ------ work on files
    output_files=[]
    nfiles = len(files)
    for ii,fname in enumerate(files):
        print(f"PROGRESS: {ii}/{nfiles}")
        fname = fname.strip()

        sfname= "%s/%s_superpixels.png" % (superoutdir, os.path.basename(fname)[0:-4])
        bfname= "%s/%s_superpixels_boundary.png" % (boutdir, os.path.basename(fname)[0:-4])


        print(f"working on file: \t {fname}", flush=True)
        print(f"saving superpixel to : \t {sfname}", flush=True)
        print(f"saving boundary to : \t {bfname}", flush=True)

        if not args.force and os.path.exists(sfname):
            print("Skipping as output file exists", flush=True)
            continue

        io = cv2.cvtColor(cv2.imread(fname), cv2.COLOR_BGR2RGB)

        # denoise
        denoised = denoise_tv_chambolle(io, weight=0.15, multichannel=True)
        denoised = rgb2gray(denoised)

        # find continuous region (low gradient) --> markers
        markers = rank.gradient(denoised, disk(1)) < 5
        markers = ndimage.label(markers)[0]

        # local gradient
        gradient = rank.gradient(denoised, disk(1))

        # watershed
        segments = watershed(gradient, markers, connectivity=1, compactness=0.0001, watershed_line=False)
        colors = np.array(  # TODO: replace with colormap approach
            [(np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255)) for i in
             range(segments.max() + 1)])

        cv2.imwrite(sfname, colors[segments])

        boundary = find_boundaries(segments, connectivity=1, mode='outer', background=0)
        boundary = boundary.astype(np.uint8) * 255

        cv2.imwrite(bfname, boundary)

        output_files.append(fname)

    print("USER: Done generating superpixels ", flush=True)
    print(f"RETVAL: {json.dumps({'output_file': output_files})}", flush=True)


except:
    track = traceback.format_exc()
    track = track.replace("\n","\t")
    print(f"ERROR: {track}", flush=True)
    sys.exit(1)




