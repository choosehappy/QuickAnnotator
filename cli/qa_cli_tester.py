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

# +
import requests
import json
import cv2
from  datetime import datetime
import base64
import numpy as np
import os
import sklearn.feature_extraction.image
import random
import argparse
import glob
import matplotlib.pyplot as plt

headers = {'Content-Type': 'application/json'}

parser = argparse.ArgumentParser(description='Import existing images with annotations into quick annotator. Note: Masks are expected to be in a subdirectory called "masks" ')
parser.add_argument('-s', '--server', help="host with port, default http://127.0.0.1:5555 ", default="http://127.0.0.1:5555", type=str)
parser.add_argument('-n', '--projname', help="project to create/add to", required=True, type=str)
parser.add_argument('-p', '--patchsize', help="Patchsize, default 256", default=256, type=int)
parser.add_argument('-r', '--stride', help="stride between ROIs, default 128", default=128, type=int)
parser.add_argument('-t', '--trainpercent', help="Percet of ROIs to use for training, default .8", default=.8 ,type=float)
parser.add_argument('-b', '--bgremove', help="Don't create ROI if patch is mostly white", action="store_true")
parser.add_argument('-m', '--numrois', help="number of ROis to randomly extract, default 3", default=3, type=int)
parser.add_argument('input_pattern', help="Input filename pattern (try: *.png)", nargs="*")

#args = parser.parse_args()
#args = parser.parse_args(["-nnuclei",r"C:\temp\qa_testsets\nuclei\*.png","-p64"])
#args = parser.parse_args(["-ntubules",r"C:\temp\qa_testsets\tubules\*.png"])
args = parser.parse_args(["-nepi",r"C:\temp\qa_testsets\epi\*.png","-m5","-r128"])


base_url=args.server
projname=args.projname
patch_size = args.patchsize
train_percent = args.trainpercent
stride = args.stride
nrois = args.numrois

img_fname = [] 
if len(args.input_pattern) > 1:  # bash has sent us a list of files
    img_fnames = args.input_pattern
elif args.input_pattern[0].endswith("txt"):  # user sent us an input file
    with open(args.input_pattern[0], 'r') as f:
        for line in f:
            img_fnames.append(line.strip())
else:  # user sent us a wildcard, need to use glob to find files
    img_fnames = glob.glob(args.input_pattern[0])



# +
img_fnames=img_fnames[3:4] #--- Limit here for testing...here this is limited to 1 image

print(f"Input pattern has resulted in {len(img_fnames)} images for uploading")

if len(img_fnames)==0:
    exit()

# +
## ----- Create Project and get Projid

filters = [dict(name='name', op='==', val=projname)]
params = dict(q=json.dumps(dict(filters=filters)))


final_url=f"{base_url}/api/db/project"
print(final_url)

response = requests.get(final_url, params=params, headers=headers)
response = response.json()
if(not response['num_results']):
    print(f"Project '{projname}' doesn't exist, creating...",end="")
    
    data = {'name': projname,'date': datetime.now().isoformat()}
    response = requests.post(final_url, json=data)
    
    if(response.status_code==201):
        print("done!")
        response = response.json()
        projid=response['id']

    else:
        print(response.text)
                        
else:
    print(f"Project '{projname}' exists....")
    projid=response['objects'][0]['id']
# -


## ---- Upload original RGB images
for img_fname in img_fnames:
    image = cv2.cvtColor(cv2.imread(img_fname), cv2.COLOR_BGR2RGB)
    img_fname_base=os.path.basename(img_fname)

    files = {'file': open(img_fname, 'rb')}
    final_url=f"{base_url}/api/{projname}/image"

    print(final_url)
    print(f"Uploading file '{img_fname}'...",end="")


    response = requests.post(final_url, files=files)
    if(response.status_code==201):
        print("done!") 
    else:
        print(response.text)


def random_subset(a, b, nitems):
    assert len(a) == len(b)
    idx = np.random.randint(0,len(a),nitems)
    return a[idx], b[idx]


## Make ROIs from images and upload. Note: this is a naive tiling approach and could be improved per use case
for img_fname in img_fnames:
    
    # load mask
    mask_fname = f'{os.path.dirname(img_fname)}{os.sep}masks{os.sep}{img_fname_base.replace(".png","_mask.png")}'#nuclei 
    mask=cv2.imread(mask_fname)


    #--- Negative class: [255,0,255], Positive class: [255,255,255], seen but unknown [0,0,255]
    [nrow,ncol,ndim]=mask.shape
    toupload = np.zeros((nrow,ncol,3),dtype=np.uint8)
    toupload[:,:,2]=255
    toupload[:,:,0]=(mask[:,:,0]==False)*255
    toupload[:,:,1]=(mask[:,:,0]>0)*255    

    #now for each ROI and its assocaited r,c coordinate we can upload
    for i in range(nrois):
    
        #encode as png
        r = np.random.randint(0,mask.shape[0]-patch_size) 
        c = np.random.randint(0,mask.shape[1]-patch_size) 
        patch = toupload[r:r+patch_size,c:c+patch_size,:]
        success, encoded_image = cv2.imencode('.png', cv2.cvtColor(patch, cv2.COLOR_RGB2BGR))

        #convert to base64
        data64 = b''.join(base64.encodebytes(encoded_image.tobytes()).splitlines())
        data64 = data64.decode('utf-8')
        data64 =u'data:image/png;base64,%s' % (data64)

        #set up request data to contain x,y location and image data
        form_data = {'roimask': data64,'pointx': c,'pointy': r}
        final_url=f"{base_url}/api/{projname}/image/{os.path.basename(img_fname)}/roimask"

        #upload
        print(f"Adding roi '{img_fname} {c}_{r}'...",end="")
        response = requests.post(final_url, data=form_data)
        if(response.status_code==201):
            print("done!") 
        else:
            print(response.text)    

# +
#--- Finally assign ROIs to training or testing set

#- get list of all ROIs available in database
final_url=f"{base_url}/api/db/project/{projid}/images"
params = {'results_per_page' : 10000} #if you have more than 10k, you should be training a model directly and importing the model
print(final_url)

response = requests.get(final_url,headers=headers, params=params)
response = response.json()
roinames=[]
for imgobj in response["objects"]:
    roisobj = imgobj['rois']
    for roi in roisobj:
        roinames.append(roi["name"])
# -

#--- random assign to training or testing
nrois=len(roinames)
indices = random.sample(range(nrois),int(nrois*train_percent))

#-- update server with designation
for ii,roiname in enumerate(roinames):
    endtype = "train" if ii in indices else "test"

    final_url = f'{base_url}/api/{projname}/dataset/{endtype}/{roiname}'
    response = requests.put(final_url)
    print(f"setting {roiname} to {endtype}: ", end="")
    if(response.status_code==200):
        print("done!") 
    else:
        print(response.text) 

#---- make patches
final_url = f'{base_url}/api/{projname}/make_patches'
response = requests.get(final_url)
make_patches_jobid=response.json()['job']['id']

# +
#--- train 
# -

#---- train AE
final_url = f'{base_url}/api/{projname}/train_autoencoder'
response = requests.get(final_url)
train_ae_jobid=response.json()['job']['id']

# +
filters = [dict(name='id', op='eq', val=train_ae_jobid)]
params = dict(q=json.dumps(dict(filters=filters)))

final_url = f'{base_url}/api/db/job'
response = requests.get(final_url, params=params, headers=headers)
response=response.json()
print(f"train AE status: {response['objects'][0]['status']}")
# -

#--- need to wait until previous cell says "Done"
#---- train TL
final_url = f'{base_url}/api/{projname}/retrain_dl'
response = requests.get(final_url)
retrain_dl_jobid=response.json()['job']['id']


# +
filters = [dict(name='id', op='eq', val=retrain_dl_jobid)]
params = dict(q=json.dumps(dict(filters=filters)))

final_url = f'{base_url}/api/db/job'
response = requests.get(final_url, params=params, headers=headers)
response=response.json()
print(f"retrain_dl  status: {response['objects'][0]['status']}")

# +
#-- need to wait until training is done
#---- get prediction of an image and display
#@api.route("/api/<project_name>/image/<image_name>/prediction", methods=['GET'])

final_url = f'{base_url}/api/{projname}/image/{img_fname_base}/prediction'
response = requests.get(final_url)


# -


img =cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
plt.imshow(img)


