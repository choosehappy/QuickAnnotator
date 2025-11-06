#%%
import threading
import ray
import time
import os
from datetime import datetime
from quickannotator.db.fsmanager import fsmanager
import builtins

from quickannotator.db import get_session
from quickannotator.db.crud.annotation import build_export_filepath, AnnotationStore
from quickannotator.dsa_sdk import DSAClient
from quickannotator.db import db_session
from quickannotator import constants
from quickannotator.db.crud.image import get_image_by_id, add_image_by_path, get_image_by_name_case_insensitive
from itertools import product
from quickannotator.constants import IMPORT_ANNOTATION_BATCH_SIZE
from quickannotator.db.logging import LoggingManager
import orjson
# import ujson
from quickannotator.db.crud.annotation_class import get_annotation_class_by_name_case_insensitive
from quickannotator.db.crud.tile import TileStoreFactory, TileStore
from tqdm import tqdm
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.geometry import Polygon, MultiPolygon
from werkzeug.datastructures import FileStorage
import logging
# logger
logger = logging.getLogger(constants.LoggerNames.FLASK.value)

def save_annotation_file_to_temp_dir(file: FileStorage):
    temp_image_path = fsmanager.nas_write.get_temp_path(relative=False)
    annot_filepath = os.path.join(temp_image_path, file.filename)

    # save annot to temp folder
    os.makedirs(temp_image_path, exist_ok=True)
    try:
        file.save(annot_filepath)
        return annot_filepath
    except IOError as e:
        logger.info(f"Saving Annotation File Error: An I/O error occurred when saving {file.filename}: {e}")
    except Exception as e:
        logger.info(f"Saving Annotation File Error: An unexpected error occurred when saving {file.filename}: {e}")

def import_annotations(image_id: int, annotation_class_id: int, isgt: bool, filepath: str):
    '''
    This is expected to be a geojson feature collection file, with each polygon being a feature.
    
    '''
    if not os.path.exists(filepath):
        logger.warning(f"File {filepath} does not exist - skipping.")
        return

    # use ujson to read fast
    with open(filepath, 'r', encoding='utf-8') as file:
        # Load the JSON data into a Python dictionary
        data = orjson.loads(file.read())
        # data = ujson.loads(file.read())
        if 'features' not in data:
            logger.error("Invalid GeoJSON: Must be a FeatureCollection containing a 'features' item - skipping")
            return
        features = data["features"]

    tile_store: TileStore = TileStoreFactory.get_tilestore()
    annotation_store = AnnotationStore(image_id, annotation_class_id, isgt, in_work_mag=False)
    all_anno = []
    for i, d in enumerate(tqdm(features)):
        all_anno.append(shape(d['geometry']))
        
        if len(all_anno)==IMPORT_ANNOTATION_BATCH_SIZE:
            anns = annotation_store.insert_annotations(all_anno)
            tile_ids = {ann.tile_id for ann in anns}
            tile_store.upsert_gt_tiles(image_id=image_id, annotation_class_id=annotation_class_id, tile_ids=tile_ids)
            db_session.commit()
            all_anno = []
    
    # commit any remaining annotations
    if all_anno:
        anns = annotation_store.insert_annotations(all_anno)
        tile_ids = {ann.tile_id for ann in anns}
        tile_store.upsert_gt_tiles(image_id=image_id, annotation_class_id=annotation_class_id, tile_ids=tile_ids)
        db_session.commit()    

    # logging message
    logger.info(f'/tImported the annotations for image {image_id} and annotation_class {annotation_class_id} from {filepath}')

def import_annotation_from_json(project_id: int, file: FileStorage):
    temp_annotation_filepath = save_annotation_file_to_temp_dir(file)
    filename = file.filename
    image_name, annotation_class_name = fsmanager.nas_write.parse_annotation_file_name(filename)
    # find the image by file name
    img = get_image_by_name_case_insensitive(project_id, image_name)
    cls = get_annotation_class_by_name_case_insensitive(project_id, annotation_class_name)
    if not img:
        logger.info(f'/tImage Name ({image_name}) not found')
        return
    if not cls:
        logger.info(f'/tAnnotation class name ({annotation_class_name}) not found')
        return 
    # import 
    import_annotations(img.id, cls.id, True, temp_annotation_filepath)

    # remove annotation file.
    try:
        os.remove(temp_annotation_filepath)
        logger.info(f"/tAnnotation json file '{temp_annotation_filepath}' deleted successfully.")
    except OSError as e:
        logger.error(f"Error deleting Annotation json file '{temp_annotation_filepath}': {e}")
  
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
class AnnotationImporter(ProgressTracker): # Inherit from ProgressTracker
    def __init__(self):
        self.logger = LoggingManager.init_logger(constants.LoggerNames.RAY.value)
        # step 1: import slide
        # step 2: import annotations
        super().__init__(2)  # Initialize ProgressTracker
        

    def import_from_tsv_row(self, project_id, data, columns, image_path_col_name=constants.TSVFields.FILE_PATH.value):
        # get slide path
        slide_path = data[image_path_col_name].strip()    
        # create slide if the slide path exist
        if not os.path.exists(fsmanager.nas_read.relative_to_global(slide_path)):
            self.logger.error(f"Slide path - {slide_path} not found")
            raise Exception(f"Slide path - {slide_path} not found")
        
        with get_session() as db_session:
            image = get_image_by_name_case_insensitive(project_id, os.path.basename(slide_path))
            if image:
                image_id = image.id
                self.logger.info(f"Image '{image_id}' already exists. Moving on to import annotations...")
            else:
                # create the image
                image = add_image_by_path(project_id, slide_path)
                image_id = image.id
                if image_id:
                    self.logger.info(f"Imported image '{image.name}' successfully")
                else:
                    self.logger.error(f"Failed to import image from path: {slide_path}")
                    raise Exception(f"Failed to import image from path: {slide_path}")

            self.increment()

            self.logger.info(f"Progress: {self.get_progress()}%")
            # Filter annotation classes ending with '_annotations'
            annot_class_names = [col for col in columns if col.endswith(constants.ANNOTATION_CLASS_SUFFIX)]
            for name in annot_class_names:
                class_name = name[:-len(constants.ANNOTATION_CLASS_SUFFIX)]
                cls = get_annotation_class_by_name_case_insensitive(project_id, class_name)
                if cls and data[name].strip():
                    import_annotations(image_id, cls.id, True, fsmanager.nas_read.relative_to_global(data[name].strip()))  

        self.increment()
        self.logger.info(f"Progress: {self.get_progress()}%")

@ray.remote(max_concurrency=2)  # Add max_concurrency=2
class AnnotationExporter(ProgressTracker):  # Inherit from ProgressTracker
    def __init__(self, image_ids, annotation_class_ids):
        self.id_pairs = [(int(image_id), int(annotation_class_id)) for image_id, annotation_class_id in product(image_ids, annotation_class_ids)]
        self.logger = LoggingManager.init_logger(constants.LoggerNames.RAY.value)
        super().__init__(len(self.id_pairs))  # Initialize ProgressTracker
        

    def export_to_dsa(self, api_uri, api_key, folder_id):
        client = DSAClient(api_uri, api_key)
        user = client.get_user_by_token()
        if user is None:
            self.logger.error("Failed to get user ID from token")
            raise Exception("Failed to get user ID from token")
        
        user_id = user['_id']
        self.logger.info(f"Starting export to DSA for user ID: {user_id}")

        for image_id, annotation_class_id in self.id_pairs:
            with get_session() as db_session:
                image_name = get_image_by_id(image_id).name
                dsa_item = client.get_item_by_name(folder_id, image_name)
                if dsa_item is None:
                    self.logger.error(f"Item with name {image_name} not found in folder {folder_id}")
                    raise Exception(f"Item with name {image_name} not found in folder {folder_id}")
                
                dsa_item_id = dsa_item['_id']
                self.logger.info(f"Exporting annotations for image: {image_name}, annotation class ID: {annotation_class_id}")
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
                            self.logger.error(f"Failed to upload chunk: {chunk_resp.status_code} {chunk_resp.text}")
                            raise Exception(f"Failed to upload chunk: {chunk_resp.status_code} {chunk_resp.text}")
                        offset += len(chunk)

            self.increment()  # Use inherited increment method
            self.logger.info(f"Progress: {self.get_progress()}%")

    def export_to_server_fs(self, formats: list[constants.AnnsFormatEnum], timestamp: datetime = None):
        """
        Export annotations remotely with support for multiple file extensions and optional timestamp.

        Args:
            timestamp (datetime, optional): Timestamp for naming the export files. Defaults to None.
            extensions (list, optional): List of file extensions to export. Defaults to ['.tar'].
        """
        self.logger.info("Starting export to server filesystem")
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
                        self.logger.info(f"Exporting to GEOJSON: {filepath}")
                        store = AnnotationStore(image_id, annotation_class_id, True, False)
                        store.export_to_geojson_file(filepath, compress=True)
            self.increment()  # Use inherited increment method
            self.logger.info(f"Progress: {self.get_progress()}%")


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


class GeometryOperation:
    """
    A class to perform geometric operations on polygons.
    """

    @staticmethod
    def union(poly1: Polygon, poly2: Polygon) -> BaseGeometry:
        """
        Perform a union operation on two polygons.

        Args:
            poly1 (Polygon): The first polygon.
            poly2 (Polygon): The second polygon.

        Returns:
            BaseGeometry: The resulting geometry after the union operation.

        Raises:
            ValueError: If either of the input polygons is not valid.
        """
        if not poly1.is_valid:
            raise ValueError("First polygon is not valid")
        if not poly2.is_valid:
            raise ValueError("Second polygon is not valid")
        result = poly1.union(poly2)

        return result

    @staticmethod
    def difference(poly1: Polygon, poly2: Polygon, multipoly_func=constants.MultiPolygonToPolygonFuncs.MAX) -> Polygon:
        """
        Perform a difference operation between two polygons.

        Args:
            poly1 (Polygon): The first polygon.
            poly2 (Polygon): The second polygon to subtract from the first.

        Returns:
            Polygon: The resulting polygon after the difference operation, or None if the result is empty.

        Raises:
            ValueError: If either of the input polygons is not valid or if the resulting polygon is invalid.
        """
        if not poly1.is_valid:
            raise ValueError("First polygon is not valid")
        if not poly2.is_valid:
            raise ValueError("Second polygon is not valid")
        result = poly1.difference(poly2)

        if result.is_empty:
            return None
        if not result.is_valid:
            raise ValueError("Resulting polygon is not valid after difference operation")
        if result.geom_type == 'MultiPolygon':
            # If the result is a MultiPolygon, return the largest polygon by area
            try:  
                func = getattr(builtins, multipoly_func.value)  
            except AttributeError:  
                raise ValueError(f"Unsupported function for handling multipolygons: {multipoly_func.value}")  

            result = func(result.geoms, key=lambda g: g.area)

        return result