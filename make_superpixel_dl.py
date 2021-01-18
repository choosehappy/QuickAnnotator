# +

import argparse
import glob
import os
import sys
import traceback

import cv2
import numpy as np
import sklearn.feature_extraction.image
import torch
from skimage.segmentation import find_boundaries
from skimage.segmentation import slic
import json


# -

class LayerActivations():
    features=None
    def __init__(self,layer):
        self.hook = layer.register_forward_hook(self.hook_fn)
    def hook_fn(self,module,input,output):
        self.features = output
    def remove(self):
        self.hook.remove()


from QA_utils import get_torch_device
from unet import UNet


# -----helper function to split data into batches
def divide_batch(l, n):
    for i in range(0, l.shape[0], n):
        yield l[i:i + n, ::]


try:
    # ----- parse command line arguments
    print("USER: Generating DL-Superpixel output with latest model", flush=True)
    parser = argparse.ArgumentParser(description='Make output for entire image using Unet')
    parser.add_argument('input_pattern',
                        help="input filename pattern. try: *.png, or tsv file containing list of files to analyze",
                        nargs="*")
    #--- gpu params
    parser.add_argument('-p', '--patchsize', help="patchsize, default 256", default=256, type=int)
    parser.add_argument('-x', '--batchsize', help="batchsize for controlling GPU memory usage, default 10", default=10,
                        type=int)
    parser.add_argument('-m', '--model', help="DL model location, default None", default=None, type=str)
    parser.add_argument('-i', '--gpuid', help="id of gpu to use, using -2 will use the CPU", default=0, type=int)
    #--- super pixel params
    parser.add_argument('-s', '--superdir', help="output dir for superpixel, default ./output/", default="./output/", type=str)
    parser.add_argument('-o', '--boundarydir', help="output dir for superpixel boundary, default ./output/", default="./output/", type=str)
    parser.add_argument('-b', '--basepath', help="base path to add to file names, helps when producing data using tsv file as input", default="", type=str)

    parser.add_argument('-a', '--approxcellsize', help="approximate width of cell in pixels, will be used to determine number of segments", default=20, type=int)
    parser.add_argument('-c', '--compactness', help="compactness of slic, default .01", default=.01, type=float)

    parser.add_argument('-f', '--force', help="force regeneration of output even if it exists", default=False,
                        action="store_true")

    args = parser.parse_known_args()[0]
    print(f"args: {args}")

    if not (args.input_pattern):
        parser.error('No images selected with input pattern')


    batch_size = args.batchsize
    patch_size = args.patchsize
    stride_size = patch_size // 2

    superoutdir = args.superdir
    boutdir = args.boundarydir

    if not os.path.exists(superoutdir):
        os.makedirs(superoutdir)

    if not os.path.exists(boutdir):
        os.makedirs(boutdir)

    # ----- load network
    device = get_torch_device(args.gpuid)

    checkpoint = torch.load(args.model, map_location=lambda storage,
                                                            loc: storage)  # load checkpoint to CPU and then put to device https://discuss.pytorch.org/t/saving-and-loading-torch-models-on-2-machines-with-different-number-of-gpu-devices/6666
    model = UNet(n_classes=checkpoint["n_classes"], in_channels=checkpoint["in_channels"],
                 padding=checkpoint["padding"], depth=checkpoint["depth"], wf=checkpoint["wf"],
                 up_mode=checkpoint["up_mode"], batch_norm=checkpoint["batch_norm"]).to(device)
    model.load_state_dict(checkpoint["model_dict"])
    model.eval()

    dr=LayerActivations(model.up_path[-1].conv_block.block[-1])


    print(f"total params: \t{sum([np.prod(p.size()) for p in model.parameters()])}")

    # ----- get file list


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
        print(f"PROGRESS: File {ii}/{nfiles}")
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

        io_shape_orig = np.array(io.shape)

        # add half the stride as padding around the image, so that we can crop it away later
        io = np.pad(io, [(stride_size // 2, stride_size // 2), (stride_size // 2, stride_size // 2), (0, 0)],
                    mode="reflect")

        io_shape_wpad = np.array(io.shape)

        # pad to match an exact multiple of unet patch size, otherwise last row/column are lost
        npad0 = int(np.ceil(io_shape_wpad[0] / patch_size) * patch_size - io_shape_wpad[0])
        npad1 = int(np.ceil(io_shape_wpad[1] / patch_size) * patch_size - io_shape_wpad[1])

        io = np.pad(io, [(0, npad0), (0, npad1), (0, 0)], mode="constant")

        arr_out = sklearn.feature_extraction.image._extract_patches(io, (patch_size, patch_size, 3), stride_size)
        arr_out_shape = arr_out.shape
        arr_out = arr_out.reshape(-1, patch_size, patch_size, 3)

        # in case we have a large network, lets cut the list of tiles into batches
        output = np.zeros((0, 4, patch_size, patch_size))
        for batch_arr in divide_batch(arr_out, batch_size):
            print(f"PROGRESS: Superpixel Chunk {output.shape[0]}/{arr_out.shape[0]}")

            arr_out_gpu = torch.from_numpy(batch_arr.transpose(0, 3, 1, 2) / 255).type('torch.FloatTensor').to(device)

            # ---- get results
            output_batch = model(arr_out_gpu)

            # --- pull from GPU and append to rest of output
            output_batch=dr.features.detach().cpu().numpy().astype(np.double)

            output = np.append(output, output_batch, axis=0)

        output = output.transpose((0, 2, 3, 1))

        # turn from a single list into a matrix of tiles
        output = output.reshape(arr_out_shape[0], arr_out_shape[1], patch_size, patch_size, output.shape[3])

        # remove the padding from each tile, we only keep the center
        output = output[:, :, stride_size // 2:-stride_size // 2, stride_size // 2:-stride_size // 2, :]

        # turn all the tiles into an image
        output = np.concatenate(np.concatenate(output, 1), 1)

        # incase there was extra padding to get a multiple of patch size, remove that as well
        output = output[0:io_shape_orig[0], 0:io_shape_orig[1], :]  # remove paddind, crop back

        # --- super pixel work
        number_segments = (output.shape[0]//args.approxcellsize)**2
        print(f"Using {number_segments} superpixels")
        segs_dl = slic(output, n_segments=number_segments, compactness=args.compactness, multichannel=True, slic_zero=True) # <--- slic_zero?


        colors = np.array(  #make random colors. its okay if some are the same, just as long as they're not touching which is unlikely
            [(np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255)) for i in
             range(segs_dl.max() + 1)])

        cv2.imwrite(sfname, colors[segs_dl])

        boundary = find_boundaries(segs_dl, connectivity=1, mode='outer', background=0)
        boundary = boundary.astype(np.uint8) * 255

        cv2.imwrite(bfname, boundary)
        output_files.append(fname)

    print("USER: Done generating output", flush=True)
    print(f"RETVAL: {json.dumps({'model': args.model,'output_file': output_files})}", flush=True)


except:
    track = traceback.format_exc()
    track = track.replace("\n","\t")
    print(f"ERROR: {track}", flush=True)
    sys.exit(1)
