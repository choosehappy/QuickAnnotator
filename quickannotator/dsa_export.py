#%%
import requests
import urllib.parse
import json

def dsa_post_file(parent_id, file_id, name, user_id, payload_size, token):
    """
    Constructs and sends an HTTP POST request to the DSA server.

    Args:
        parent_id (str): The parent ID for the request.
        name (str): The name of the file.
        user_id (str): The user ID for the request.
        payload (str): The JSON payload to include in the request.
        token (str): The Girder authentication token.

    Returns:
        Response: The response object from the HTTP request.
    """
    reference = {
        "identifier": "LargeImageAnnotationUpload",
        "itemId": parent_id,
        "fileId": file_id,
        "userId": user_id
    }

    # Construct the URL
    url_params = {
        "parentType": "item",
        "parentId": parent_id,
        "name": name,
        "size": payload_size,
        "reference": json.dumps(reference),
    }
    url = "http://somai-serv04.emory.edu:5000/api/v1/file?"
    url += urllib.parse.urlencode(url_params)

    headers = {
        'Girder-Token': token,
        'Content-Type': 'text/plain'
    }
    response = requests.post(url, headers=headers)
    return response


def dsa_post_file_chunk(chunk, token, upload_id, offset):
    """
    Constructs and sends an HTTP POST request to the DSA server.

    Args:
        chunk (str): The chunk of data to send.
        token (str): The Girder authentication token.

    Returns:
        Response: The response object from the HTTP request.
    """
    url_params = {
        "uploadId": upload_id,
        "offset": offset,
    }
    url = "http://somai-serv04.emory.edu:5000/api/v1/file/chunk?"
    url += urllib.parse.urlencode(url_params)
    headers = {
        'Girder-Token': token,
        'Content-Type': 'text/plain'
    }
    response = requests.post(url, headers=headers, data=chunk)
    return response


def dsa_get_token_with_api_key(key, duration=1):
    """
    Retrieves a temporary token using an API key.

    Args:
        key (str): The API key to use for generating the token.
        duration (int): The duration (in hours) for which the token is valid.
        girder_token (str, optional): The Girder authentication token, if required.

    Returns:
        str: The temporary token.
    """
    url_params = {
        "key": key,
        "duration": duration
    }
    url = "http://somai-serv04.emory.edu:5000/api/v1/api_key/token?"
    url += urllib.parse.urlencode(url_params)

    headers = {
        'accept': 'application/json'
    }

    response = requests.post(url, headers=headers, data='')

    if response.status_code == 200:
        return response.json().get('token')
    else:
        raise Exception(f"Failed to retrieve token: {response.status_code} {response.text}")


# Example usage
#%%
parent_id = "681d1881f39ed19f8523b72b"
file_id = "681d1881f39ed19f8523b72c"
name = "10_26609_028_502%20L5%20PAS.geojson"
user_id = "681d13553ab94dbb6772e1d4"
payload = "{\"type\":\"FeatureCollection\",\"features\":[{\"type\":\"Feature\",\"id\":\"fa622173-6fa0-4fa4-aeff-ec590fdeb587\",\"geometry\":{\"type\":\"Polygon\",\"coordinates\":[[[17052, 6480],[16906, 6528],[16808, 6528],[16711, 6577],[16467, 6577],[16467, 6626],[16029, 6626],[15932, 6675],[15883, 6675],[15688, 6772],[15591, 6772],[15542, 6821],[15493, 6869],[15445, 6869],[15347, 6967],[15250, 6967],[15201, 7015],[15153, 7015],[15055, 7064],[15006, 7113],[14909, 7162],[14812, 7308],[14714, 7356],[14617, 7454],[14471, 7502],[14325, 7600],[14227, 7648],[14130, 7746],[13984, 7795],[13886, 7892],[13789, 7941],[13740, 8038],[13692, 8087],[13594, 8135],[13594, 8233],[13546, 8282],[13497, 8330],[13448, 8379],[13400, 8428],[13351, 8525],[13302, 8574],[13253, 8622],[13205, 8671],[13156, 8720],[13156, 8768],[13156, 8817],[13107, 8866],[13107, 8915],[13107, 8963],[13107, 9012],[13059, 9012],[13059, 9061],[13059, 9109],[13010, 9207],[13010, 9255],[13010, 9353],[12961, 9450],[12961, 9548],[12913, 9645],[12913, 9694],[12913, 9742],[12913, 9791],[12913, 9840],[12913, 9937],[12913, 9986],[12913, 10083],[12913, 10132],[12913, 10229],[12913, 10278],[12913, 10327],[12913, 10375],[12913, 10424],[12913, 10473],[12913, 10521],[12913, 10619],[12913, 10668],[12913, 10765],[12913, 10862],[12913, 10911],[12913, 11008],[12913, 11106],[12913, 11203],[12913, 11252],[12913, 11349],[12913, 11447],[12913, 11544],[12864, 11641],[12864, 11739],[12864, 11788],[12815, 11885],[12815, 11934],[12767, 12031],[12767, 12080],[12718, 12128],[12718, 12177],[12669, 12226],[12669, 12323],[12620, 12372],[12620, 12469],[12572, 12518],[12572, 12567],[12523, 12615],[12474, 12664],[12426, 12713],[12377, 12713],[12280, 12761],[12231, 12810],[12182, 12859],[12133, 12908],[12036, 12956],[11987, 13005],[11890, 13054],[11744, 13054],[11647, 13102],[11500, 13102],[11354, 13151],[11208, 13151],[11111, 13200],[11013, 13248],[10916, 13248],[10819, 13297],[10770, 13346],[10673, 13346],[10624, 13395],[10380, 13395],[10332, 13443],[10283, 13492],[10234, 13541],[10186, 13541],[10137, 13589],[10088, 13638],[10040, 13687],[9991, 13687],[9991, 13735],[9942, 13735],[9942, 13784],[9893, 13833],[9845, 13881],[9796, 13930],[9747, 14028],[9699, 14125],[9601, 14222],[9553, 14271],[9455, 14368],[9407, 14466],[9309, 14612],[9260, 14709],[9212, 14807],[9163, 14904],[9066, 15001],[9017, 15099],[9017, 15196],[8968, 15294],[8968, 15342],[8968, 15440],[8968, 15488],[8968, 15537],[8968, 15586],[8968, 15634],[8968, 15683],[8968, 15732],[9017, 15781],[9066, 15829],[9066, 15878],[9114, 15927],[9114, 15975],[9163, 15975],[9163, 16024],[9212, 16024],[9212, 16073],[9260, 16073],[9260, 16121],[9309, 16170],[9358, 16219],[9407, 16219],[9455, 16268],[9504, 16316],[9553, 16316],[9601, 16365],[9650, 16414],[9942, 16414],[9991, 16365],[10040, 16365],[10040, 16316],[10088, 16316],[10137, 16268],[10234, 16268],[10283, 16219],[10332, 16219],[10429, 16170],[10478, 16121],[10527, 16121],[10575, 16073],[10624, 16024],[10673, 15975],[10721, 15927],[10770, 15927],[10770, 15878],[10819, 15878],[10867, 15829],[10916, 15829],[10965, 15781],[11013, 15732],[11111, 15732],[11160, 15683],[11208, 15683],[11208, 15634],[11403, 15440],[11452, 15391],[11500, 15342],[11549, 15342],[11598, 15294],[11647, 15245],[11695, 15196],[11744, 15196],[11793, 15148],[11841, 15099],[11890, 15099],[11890, 15050],[11939, 15001],[11987, 14953],[12085, 14904],[12133, 14855],[12231, 14807],[12280, 14758],[12377, 14709],[12426, 14661],[12620, 14466],[12669, 14466],[12669, 14417],[12718, 14368],[12767, 14320],[12815, 14271],[12864, 14222],[12913, 14174],[13010, 14125],[13059, 14125],[13107, 14076],[13156, 14076],[13205, 14028],[13253, 13979],[13253, 13930],[13302, 13881],[13351, 13833],[13400, 13784],[13497, 13735],[13546, 13687],[13594, 13638],[13643, 13589],[13692, 13492],[13789, 13443],[13838, 13395],[13886, 13297],[13984, 13200],[14081, 13054],[14227, 12956],[14325, 12908],[14373, 12859],[14568, 12761],[14617, 12713],[14666, 12664],[14666, 12615],[14714, 12615],[14714, 12567],[14763, 12518],[14812, 12469],[14860, 12421],[14909, 12372],[14958, 12323],[15055, 12275],[15104, 12226],[15153, 12177],[15201, 12128],[15250, 12080],[15347, 11982],[15542, 11885],[15640, 11885],[15688, 11836],[15737, 11836],[15737, 11788],[15786, 11739],[15834, 11739],[15834, 11690],[15883, 11690],[15980, 11593],[16078, 11495],[16078, 11447],[16126, 11398],[16175, 11398],[16175, 11349],[16175, 11301],[16273, 11008],[16321, 10960],[16370, 10862],[16419, 10765],[16467, 10716],[16516, 10668],[16516, 10570],[16516, 10473],[16565, 10375],[16565, 10278],[16565, 10181],[16565, 10083],[16565, 9986],[16565, 9937],[16565, 9888],[16565, 9840],[16565, 9791],[16565, 9742],[16565, 9694],[16565, 9645],[16565, 9450],[16565, 9401],[16565, 9353],[16565, 9255],[16565, 9207],[16565, 8915],[16565, 8817],[16565, 8768],[16565, 8720],[16565, 8671],[16565, 8622],[16565, 8574],[16613, 8525],[16613, 8476],[16613, 8428],[16662, 8428],[16662, 8379],[16711, 8379],[16760, 8330],[17100, 8330],[17149, 8379],[17198, 8379],[17246, 8428],[17587, 8428],[17636, 8476],[18220, 8476],[18318, 8428],[18318, 8379],[18366, 8379],[18415, 8330],[18464, 8282],[18513, 8233],[18561, 8184],[18610, 8135],[18659, 8135],[18659, 8087],[18707, 8087],[18756, 8038],[18756, 7989],[18805, 7989],[18805, 7892],[18805, 7843],[18805, 7795],[18805, 7746],[18805, 7697],[18805, 7648],[18853, 7600],[18853, 7551],[18853, 7502],[18853, 7454],[18853, 7405],[18853, 7356],[18853, 7308],[18853, 7259],[18853, 7210],[18853, 7162],[18853, 7113],[18756, 7015],[18659, 7015],[18659, 6967],[18610, 6967],[18610, 6918],[18513, 6918],[18513, 6869],[18464, 6869],[17831, 6480],[17052, 6480]]]},\"properties\":{\"objectType\":\"annotation\"}}]}"
payload_size = len(payload)
token = "te0hM66OhFPf1qintnLbTiG56YFn4GOA2GcUHvRclLDHq2LZGCeyzUhPnychFlHh"
#%%
response = dsa_post_file(parent_id, file_id, name, user_id, payload_size, token)

#%%
upload_id = response.json()['_id']
# %%
chunk_size = 1024 * 1024  # 1 MB
offset = 0

while offset < payload_size:
    chunk = payload[offset:offset + chunk_size]
    response = dsa_post_file_chunk(chunk, token, upload_id, offset)
    if response.status_code != 200:
        print(f"Error uploading chunk at offset {offset}: {response.text}")
        break
    if response.status_code == 200:
        print(f"Uploaded chunk at offset {offset}")
    offset += chunk_size

print(response.text)
# %%
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.dsa_sdk import DSAClient
from quickannotator.db import get_session
import ray
import numpy as np
import time
import asyncio

# %%
base_url = "http://somai-serv04.emory.edu:5000"
api_key = 'ynklVBL4CCoVj7YPxzZlXDiAvgICaKbEXbD6Kfu8'
parent_id = "681da5dcf39ed19f8523b7ef"

user_id = "681d13553ab94dbb6772e1d4"

#%%


@ray.remote
class ProgressTracker:
    def __init__(self, total):
        self.total = total
        self.progress = 0

    def increment(self):
        self.progress += 1

    def get_progress(self):
        return (self.progress / self.total) * 100


@ray.remote
class AnnotationExporter:
    def __init__(self, image_ids, annotation_class_ids, progress_actor):
        self.id_tuples = np.array(np.meshgrid(image_ids, annotation_class_ids)).T.reshape(-1, 2).tolist()
        self.progress_actor = progress_actor

    def process_annotations(self, base_url, api_key, parent_id, user_id):
        client = DSAClient(base_url, api_key)
        for image_id, annotation_class_id in self.id_tuples:
            with get_session() as db_session:
                store = AnnotationStore(image_id, annotation_class_id, True, False)
                store.export_annotations_to_dsa(client, parent_id, user_id)
            self.progress_actor.increment.remote()  # Async, won't block



# example usage
image_ids = [1]
annotation_class_ids = [1,2]
progress_actor = ProgressTracker.remote(len(image_ids) * len(annotation_class_ids))
exporter = AnnotationExporter.remote(image_ids, annotation_class_ids, progress_actor)

exporter.process_annotations.remote(base_url, api_key, parent_id, user_id)

# poll for progress
while True:
    progress = ray.get(progress_actor.get_progress.remote())
    print(f"Progress: {progress:.2f}%")
    if progress >= 100:
        break
    time.sleep(1)

# %%
