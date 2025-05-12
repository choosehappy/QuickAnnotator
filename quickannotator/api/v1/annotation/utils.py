#%%
import numpy as np
import ray
import time
import os

from quickannotator.db import get_session
from quickannotator.db.utils import FileSystemManager, build_annotation_table_name
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.dsa_sdk import DSAClient
import geojson
from quickannotator import constants
from quickannotator.db.crud.image import get_image_by_id


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
        image_ids_grid, annotation_class_ids_grid = np.meshgrid(image_ids, annotation_class_ids, indexing='ij')
        self.id_pairs = list(zip(image_ids_grid.ravel(), annotation_class_ids_grid.ravel()))
        self.progress_actor = progress_actor

    def export_to_dsa(self, api_uri, api_key, folder_id):
        client = DSAClient(api_uri, api_key)
        user = client.get_user_by_token()
        if user is None:
            raise Exception("Failed to get user ID from token")
        
        user_id = user['_id']

        for image_id, annotation_class_id in self.id_pairs:
            with get_session() as db_session:
                image_name = get_image_by_id(image_id).name
                dsa_item = client.get_item_by_name(folder_id, image_name)
                if dsa_item is None:
                    raise Exception(f"Item with name {image_name} not found in folder {folder_id}")
                
                dsa_item_id = dsa_item['_id']
                store = AnnotationStore(image_id, annotation_class_id, True, False)
                feature_collection = store.get_all_annotations_as_feature_collection()    # TODO: this should probably be done with tempfile to avoid memory issues
                feature_collection_json = geojson.dumps(feature_collection)
                fc_bytes = feature_collection_json.encode('utf-8')
                upload_id = client.post_file(
                    parent_id=dsa_item_id,
                    file_id=hex(int(dsa_item_id, 16) + 1)[2:].zfill(24),  # TODO: this is janky, ideally should be done by
                    name="annotations.geojson",
                    user_id=user_id,
                    payload_size=len(fc_bytes)
                )
        
                offset = 0
                while offset < len(fc_bytes):
                    chunk = fc_bytes[offset:offset + constants.POST_FILE_CHUNK_SIZE]
                    chunk_resp = client.post_file_chunk(chunk, upload_id, offset=offset)
                    if chunk_resp.status_code != 200:
                        raise Exception(f"Failed to upload chunk: {chunk_resp.status_code} {chunk_resp.text}")
                    offset += constants.POST_FILE_CHUNK_SIZE

            self.progress_actor.increment.remote()  # Async, won't block

    def export_remotely(self, project_id):
        fsman = FileSystemManager()

        for image_id, annotation_class_id in self.id_pairs:
            with get_session() as db_session:
                save_path = fsman.get_project_mask_path(project_id, image_id)
                table_name = build_annotation_table_name(image_id, annotation_class_id, True)
                tarpath = os.path.join(save_path, f'{table_name}.tar')
                store = AnnotationStore(image_id, annotation_class_id, True, False) # NOTE: may need to set in_work_mag to false
                store.export_all_annotations_to_tar(tarpath)

                
                
# %%
base_url = "http://somai-serv04.emory.edu:5000"
api_key = 'ynklVBL4CCoVj7YPxzZlXDiAvgICaKbEXbD6Kfu8'
folder_id = "681d185bf39ed19f8523b729"
