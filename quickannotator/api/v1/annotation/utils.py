#%%
import threading
import numpy as np
import ray
import time
import os

from quickannotator.db import get_session
from quickannotator.db.utils import build_annotation_table_name, build_tarpath
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.dsa_sdk import DSAClient
import geojson
from quickannotator import constants
from quickannotator.db.crud.image import get_image_by_id
from itertools import product


class ProgressTracker:
    def __init__(self, total: int):
        self.total = total
        self.progress = 0
        self.lock = threading.Lock()  # Add a threading lock for thread safety

    def increment(self):
        with self.lock:  # Ensure thread safety by locking during increment
            self.progress += 1

    def get_progress(self) -> float:
        with self.lock:  # Lock when accessing progress
            return (self.progress / self.total) * 100


@ray.remote(max_concurrency=2)  # Add max_concurrency=2
class AnnotationExporter(ProgressTracker):  # Inherit from ProgressTracker
    def __init__(self, image_ids, annotation_class_ids):
        self.id_pairs = [(int(image_id), int(annotation_class_id)) for image_id, annotation_class_id in product(image_ids, annotation_class_ids)]
        super().__init__(len(self.id_pairs))  # Initialize ProgressTracker
        

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
                store = AnnotationStore(image_id, annotation_class_id, True, False, False)
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

            self.increment()  # Use inherited increment method

    def export_remotely(self):
        for image_id, annotation_class_id in self.id_pairs:
            with get_session() as db_session:
                tarpath = build_tarpath(image_id, annotation_class_id, is_gt=True)
                store = AnnotationStore(image_id, annotation_class_id, True, False, False)
                store.export_all_annotations_to_tar(tarpath)
            self.increment()  # Use inherited increment method


def compute_actor_name(project_id: int, type: constants.NamedRayActorType=constants.NamedRayActorType.ANNOTATION_EXPORTER) -> str:
    """
    Generate a unique name for the actor using project ID and current timestamp.
    
    Args:
        project_id (int): The ID of the project.
        type (constants.NamedRayActorType): The type of the actor.
    
    Returns:
        str: The generated actor name.
    """
    timestamp = time.strftime('%Y%m%d%H%M%S')
    return f"{project_id}_{type.value}_{timestamp}"