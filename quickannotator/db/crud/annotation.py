from sqlalchemy.orm import Query
import quickannotator.db.models as db_models
import quickannotator.constants as constants
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor, get_tilespace
from quickannotator.db import Base, db_session
from quickannotator.db.crud.misc import compute_custom_metrics
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from quickannotator.dsa_sdk import DSASDK


import sqlalchemy
from shapely.affinity import scale
from shapely.geometry.base import BaseGeometry
from sqlalchemy import func


from datetime import datetime
from typing import List
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Query
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor, get_tilespace
from quickannotator.db import db_session, Base
import quickannotator.db.models as models
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from quickannotator.db.logging import qa_logger
import geojson
from io import BytesIO
import tarfile
import json


def get_annotation_query(model, scale_factor: float=1.0) -> Query:
    '''
    Constructs a SQLAlchemy query to retrieve and scale annotation data from the database.
    Args:
        model: The SQLAlchemy model class representing the annotation table.
        scale_factor: The factor by which to scale the geometries.
    Returns:
        Query: A SQLAlchemy query object that retrieves the following fields from the annotation table:
            - id: The unique identifier of the annotation.
            - tile_id: The identifier of the tile associated with the annotation.
            - centroid: The scaled centroid of the annotation polygon in GeoJSON format.
            - polygon: The scaled annotation polygon in GeoJSON format.
            - area: The area of the annotation polygon.
            - custom_metrics: Custom metrics associated with the annotation.
            - datetime: The datetime when the annotation was created or last modified.
    '''

    if scale_factor <= 0:
        raise ValueError("scale_factor must be greater than 0.")

    query = db_session.query(
        model.id,
        model.tile_id,
        func.ST_AsGeoJSON(func.ST_Scale(model.centroid, scale_factor, scale_factor)).label('centroid'),
        func.ST_AsGeoJSON(func.ST_Scale(model.polygon, scale_factor, scale_factor)).label('polygon'),
        model.area,
        model.custom_metrics,
        model.datetime
    )

    return query


def anns_to_feature_collection(annotations: List[models.Annotation]) -> geojson.FeatureCollection:
    """
    Converts a list of annotations to a GeoJSON FeatureCollection.

    Args:
        annotations (List[models.Annotation]): A list of annotation objects.

    Returns:
        geojson.FeatureCollection: A GeoJSON FeatureCollection containing the annotations.
    """
    features = []
    for annotation in annotations:
        feature = geojson.Feature(
            id=annotation.id,
            geometry=geojson.loads(annotation.polygon),
            properties={
                # 'id': annotation.id,
                # 'tile_id': annotation.tile_id,
                # 'centroid': geojson.loads(annotation.centroid),
                # 'area': annotation.area,
                # 'custom_metrics': annotation.custom_metrics,
                # 'datetime': annotation.datetime.isoformat()
                'objectType': 'annotation'

            }
        )
        features.append(feature)
    
    return geojson.FeatureCollection(features)

# TODO: Remove this function and use the one in AnnotationStore instead.
def stream_annotations_tar(tablenames: List[str]):
    with BytesIO() as tar_buffer:
        with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
            for i, table_name in enumerate(tablenames):
                try:
                    # Attempt to create a dynamic model for the table
                    model = create_dynamic_model(table_name)
                    annotations = get_annotation_query(model).all()
                    feature_collection = anns_to_feature_collection(annotations)
                    feature_collection_json = geojson.dumps(feature_collection)

                    # Create a tarinfo object for the GeoJSON file
                    tarinfo = tarfile.TarInfo(name=f"{table_name}.geojson")
                    tarinfo.size = len(feature_collection_json)

                    # Add the GeoJSON file to the tar archive
                    tar.addfile(tarinfo, BytesIO(feature_collection_json.encode('utf-8')))
                except sqlalchemy.exc.NoSuchTableError:
                    qa_logger.info(f"Table {table_name} does not exist. Skipping.")
                    continue
                except Exception as e:
                    qa_logger.error(f"Error processing table {table_name}: {e}")
                    continue

                # Flush the tar buffer and yield its content in chunks
                tar_buffer.seek(0)
                while chunk := tar_buffer.read(constants.STREAMING_CHUNK_SIZE):  # Read in 8KB chunks
                    yield chunk
                tar_buffer.seek(0)  # Reset buffer position
                tar_buffer.truncate(0)  # Clear the buffer after yielding



class AnnotationStore:
    def __init__(self, image_id: int, annotation_class_id: int, is_gt: bool, in_work_mag=True, create_table=False):
        """
        Initializes the annotation helper with the given parameters.

        Args:
            image_id (int): The ID of the image.
            annotation_class_id (int): The ID of the annotation class.
            is_gt (bool): A flag indicating whether the annotation is ground truth.
            in_work_mag (bool, optional): If True, all input and output polygons are in working magnification. Defaults to True. 
                If False, all input and output polygons are in base magnification.
            create_table_if_non_existent (bool, optional): If True, creates the annotation table if it does not exist. Defaults to False.

        Attributes:
            image_id (int): The ID of the image.
            annotation_class_id (int): The ID of the annotation class.
            is_gt (bool): A flag indicating whether the annotation is ground truth.
            model: The dynamic model created for the annotation.
            scaling_factor (float): The base to work scaling factor.
        """

        self.image_id = image_id
        self.annotation_class_id = annotation_class_id
        self.is_gt = is_gt
        self.scaling_factor = 1.0 if in_work_mag else base_to_work_scaling_factor(image_id, annotation_class_id)

        if create_table:
            model = self.create_annotation_table(image_id, annotation_class_id, is_gt)
            self.model = model
        else:
            self.model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, is_gt=is_gt))


    # CREATE
    # TODO: consider adding optional parameter to allow tileids to be passed in.
    def insert_annotations(self, polygons: List[BaseGeometry], tile_ids: List[int] | int=None) -> List[db_models.Annotation]:
        # Initial validation
        if len(polygons) == 0:
            return []

        if not isinstance(tile_ids, list):
            tile_ids = [tile_ids] * len(polygons)   # By default produce a list of None values.

        if len(polygons) != len(tile_ids):
            raise ValueError("The lengths of polygons and tile_ids must match.")

        # in_work_mag is true because we expect the polygons are scaled at this point.
        tilespace = get_tilespace(self.image_id, self.annotation_class_id, in_work_mag=True)
        new_annotations = []

        for polygon, tile_id in zip(polygons, tile_ids):
            scaled_polygon = self.scale_polygon(polygon, self.scaling_factor)

            if tile_id is None:
                tile_id = tilespace.point_to_tileid(scaled_polygon.centroid.x, scaled_polygon.centroid.y)

            new_annotations.append({
                "tile_id": tile_id,  # Ensure correct value
                "centroid": scaled_polygon.centroid.wkt,
                "polygon": scaled_polygon.wkt,
                "area": scaled_polygon.area,
                "custom_metrics": compute_custom_metrics(),  # Add appropriate custom metrics if needed
                "datetime": datetime.now()
            })

        stmt = sqlalchemy.insert(self.model).returning(self.model.id).values(new_annotations)
        ids = db_session.scalars(stmt).all()
        result = self.get_annotations_by_ids(annotation_ids=ids)    # Must do this otherwise scaling etc. does not apply.

        return result


    # READ
    def get_annotation_by_id(self, annotation_id: int) -> db_models.Annotation:
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter_by(id=annotation_id).first()
        return result


    def get_annotations_by_ids(self, annotation_ids: List[int]) -> List[db_models.Annotation]:
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter(self.model.id.in_(annotation_ids)).all()
        return result


    def get_annotations_for_tiles(self, tile_ids: List[int]) -> List[db_models.Annotation]:
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter(self.model.tile_id.in_(tile_ids)).all()
        return result
    

    def get_all_annotations(self) -> List[models.Annotation]:
        result = get_annotation_query(self.model, 1/self.scaling_factor).all()
        return result


    def get_annotations_within_poly(self, polygon: BaseGeometry) -> List[db_models.Annotation]:
        scaled_polygon = self.scale_polygon(polygon, self.scaling_factor)
        # NOTE: Sqlite may not use the spatial index here.
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter(func.ST_Intersects(self.model.polygon, func.ST_GeomFromText(scaled_polygon.wkt, 0))).all()
        return result
    

    def export_all_annotations_to_tar(self, tarname: str):
        """
        Saves all annotations to a tar archive.

        Args:
            tarname (str): The name of the tar file to save the annotations to.
        """
        with tarfile.open(tarname, mode='w') as tar:
            annotations = self.get_all_annotations()
            feature_collection = anns_to_feature_collection(annotations)
            feature_collection_json = geojson.dumps(feature_collection)

            # Create a tarinfo object for the GeoJSON file
            tarinfo = tarfile.TarInfo(name=f"{self.get_annotation_table_name()}.geojson")
            tarinfo.size = len(feature_collection_json)

            # Add the GeoJSON file to the tar archive
            tar.addfile(tarinfo, BytesIO(feature_collection_json.encode('utf-8')))

    def export_annotations_to_dsa(self, base_url: str, api_key: str, parent_id: str, user_id: str, name: str):
        dsa_sdk = DSASDK(base_url=base_url, api_key=api_key)

        annotations = self.get_all_annotations()
        feature_collection = anns_to_feature_collection(annotations)
        feature_collection_json = geojson.dumps(feature_collection)
        feature_collection_bytes = feature_collection_json.encode('utf-8')

        upload_id = dsa_sdk.post_file(
            parent_id=parent_id,
            file_id=hex(int(parent_id, 16) + 1)[2:].zfill(24),  # TODO: this is janky, ideally should be done by
            name=name,
            user_id=user_id,
            payload_size=len(feature_collection_bytes)
        )
        
        offset = 0
        while offset < len(feature_collection_bytes):
            chunk = feature_collection_bytes[offset:offset + constants.POST_FILE_CHUNK_SIZE]
            chunk_resp = dsa_sdk.post_file_chunk(chunk, upload_id, offset=offset)
            if chunk_resp.status_code != 200:
                raise Exception(f"Failed to upload chunk: {chunk_resp.status_code} {chunk_resp.text}")
            offset += constants.POST_FILE_CHUNK_SIZE




    # UPDATE
    def update_annotation(self, annotation_id: int, polygon: BaseGeometry) -> db_models.Annotation:
        scaled_polygon = self.scale_polygon(polygon, self.scaling_factor)
        tile_id = get_tilespace(self.image_id, self.annotation_class_id).point_to_tileid(
            scaled_polygon.centroid.x, scaled_polygon.centroid.y
        )

        annotation = db_session.query(self.model).filter(self.model.id == annotation_id).first()

        if annotation:
            annotation.tile_id = tile_id
            annotation.centroid = scaled_polygon.centroid.wkt
            annotation.polygon = scaled_polygon.wkt
            annotation.area = scaled_polygon.area
            annotation.custom_metrics = compute_custom_metrics()
            annotation.datetime = datetime.now()
            db_session.commit()
            return self.get_annotation_by_id(annotation_id)  # Get the updated annotation by id

        return None  # Handle case where annotation_id is not found


    # DELETE
    def delete_annotation(self, annotation_id: int) -> int:
        """
        Deletes an annotation by its ID.
        Args:
            annotation_id (int): The ID of the annotation to be deleted.
        Returns:
            int: The ID of the deleted annotation if it exists, otherwise None.
        """

        stmt = sqlalchemy.delete(self.model).where(self.model.id == annotation_id).returning(self.model.id)
        result = db_session.execute(stmt).scalar_one_or_none()
        db_session.commit()
        return result


    def delete_annotations(self, annotation_ids: List[int]) -> List[int]:
        """
        Deletes multiple annotations by their IDs.
        Args:
            annotation_ids (List[int]): A list of annotation IDs to be deleted.
        Returns:
            List[int]: A list of the IDs of the deleted annotations.
        """

        stmt = sqlalchemy.delete(self.model).where(self.model.id.in_(annotation_ids)).returning(self.model.id)
        result = db_session.execute(stmt).scalars().all()
        db_session.commit()
        return result


    def delete_annotations_by_tile(self, tile_id: int) -> List[int]:
        """
        Deletes all annotations associated with a tile.
        Args:
            tile_id (int): The ID of the tile.
        Returns:
            List[int]: A list of the IDs of the deleted annotations.
        """

        stmt = sqlalchemy.delete(self.model).where(self.model.tile_id == tile_id).returning(self.model.id)
        result = db_session.execute(stmt).scalars().all()
        db_session.commit()
        return result


    def delete_all_annotations(self):
        db_session.query(self.model).delete()


    # MISC
    def get_annotation_table_name(self) -> str:
        """
        Returns the name of the annotation table.
        """
        return build_annotation_table_name(self.image_id, self.annotation_class_id, is_gt=self.is_gt)
    

    @staticmethod
    def create_annotation_table(image_id: int, annotation_class_id: int, is_gt: bool):
        table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt=is_gt)
        table = db_models.Annotation.__table__.to_metadata(Base.metadata, name=table_name)
        Base.metadata.create_all(bind=db_session.bind, tables=[table])

        return create_dynamic_model(table_name)


    @staticmethod
    def scale_polygon(polygon: BaseGeometry, scaling_factor: float) -> BaseGeometry:   # Added for safety - I've forgotten the origin param several times.
        return scale(polygon, xfact=scaling_factor, yfact=scaling_factor, origin=(0, 0))