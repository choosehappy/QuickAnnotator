#%%
import threading
import numpy as np
import ray
import time
import os
from datetime import datetime

from quickannotator.db import get_session
from quickannotator.db.utils import build_export_filepath
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
            if self.progress < self.total:
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
                store = AnnotationStore(image_id, annotation_class_id, True, False)
                geojson_file_path = store.export_to_geojson_file()  # Use export_to_geojson_file to get the file path
                upload_id = client.post_file(
                    parent_id=dsa_item_id,
                    file_id=hex(int(dsa_item_id, 16) + 1)[2:].zfill(24),  # NOTE: The DSA docs do not specify how to generate file_id, so we use a simple increment based on item ID
                    name="annotations.geojson",
                    user_id=user_id,
                    payload_size=os.path.getsize(geojson_file_path)  # Get file size for payload
                )
        
                offset = 0
                with open(geojson_file_path, 'rb') as f:
                    while chunk := f.read(constants.POST_FILE_CHUNK_SIZE):  # Read file incrementally
                        chunk_resp = client.post_file_chunk(chunk, upload_id, offset=offset)
                        if chunk_resp.status_code != 200:
                            raise Exception(f"Failed to upload chunk: {chunk_resp.status_code} {chunk_resp.text}")
                        offset += len(chunk)

            self.increment()  # Use inherited increment method

    def export_to_server_fs(self, formats: list[constants.AnnsFormatEnum], timestamp: datetime = None):
        """
        Export annotations remotely with support for multiple file extensions and optional timestamp.

        Args:
            timestamp (datetime, optional): Timestamp for naming the export files. Defaults to None.
            extensions (list, optional): List of file extensions to export. Defaults to ['.tar'].
        """

        for image_id, annotation_class_id in self.id_pairs:
            with get_session() as db_session:
                for format in formats:
                    if format == constants.AnnsFormatEnum.GEOJSON:
                        filepath = build_export_filepath(
                            image_id=image_id,
                            annotation_class_id=annotation_class_id,
                            is_gt=True,
                            extension=constants.ExportFormatExtensions.GEOJSON,
                            relative=False,
                            timestamp=timestamp
                        )
                        store = AnnotationStore(image_id, annotation_class_id, True, False)
                        store.export_to_geojson_file(filepath, compress=True)
            self.increment()  # Use inherited increment method


def compute_actor_name(project_id: int, type: constants.NamedRayActorType) -> str:
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