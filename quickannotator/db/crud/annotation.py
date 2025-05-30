from sqlalchemy.orm import Query
import quickannotator.db.models as db_models
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor, get_tilespace
from quickannotator.db import Base, db_session, get_ogr_datasource
from quickannotator.db.crud.misc import compute_custom_metrics
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model, get_query_as_sql
import sqlalchemy
from shapely.affinity import scale
from shapely.geometry.base import BaseGeometry
from sqlalchemy import func
from datetime import datetime
from typing import List
import geojson
import json
import os
import gzip
from osgeo import ogr
import tempfile


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


def anns_to_feature_collection(annotations: List[db_models.Annotation]) -> geojson.FeatureCollection:
    """
    Converts a list of annotations to a GeoJSON FeatureCollection.

    Args:
        annotations (List[models.Annotation]): A list of annotation objects.

    Returns:
        geojson.FeatureCollection: A GeoJSON FeatureCollection containing the annotations.
    """
    features = [
        geojson.Feature(
            id=annotation.id,
            geometry=geojson.loads(annotation.polygon), # NOTE: potentially optimize using orjson.loads
            properties={
                'objectType': 'annotation'
            }
        )
        for annotation in annotations
    ]
    
    return geojson.FeatureCollection(features)


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

        self.query = get_annotation_query(self.model, 1/self.scaling_factor)

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
        result = self.query.filter_by(id=annotation_id).first()
        return result


    def get_annotations_by_ids(self, annotation_ids: List[int]) -> List[db_models.Annotation]:
        result = self.query.filter(self.model.id.in_(annotation_ids)).all()
        return result


    def get_annotations_for_tiles(self, tile_ids: List[int]) -> List[db_models.Annotation]:
        result = self.query.filter(self.model.tile_id.in_(tile_ids)).all()
        return result
    

    def get_all_annotations(self) -> List[db_models.Annotation]:
        result = self.query.all()
        return result


    def get_annotations_within_poly(self, polygon: BaseGeometry) -> List[db_models.Annotation]:
        scaled_polygon = self.scale_polygon(polygon, self.scaling_factor)
        # NOTE: Sqlite may not use the spatial index here.
        result = self.query.filter(func.ST_Intersects(self.model.polygon, func.ST_GeomFromText(scaled_polygon.wkt, 0))).all()
        return result
    

    def export_to_geojson_file(self, filepath: str = None, compress: bool = False) -> str:
        """
        Streams annotations to a GeoJSON file to handle large datasets efficiently.
        Optionally compresses the output file as gzip.

        Args:
            filepath (str, optional): Output path. Temporary file is used if None.
            compress (bool, optional): Whether to gzip the output. Note that Digital Slide Archive does not accept gzip geojson files.

        Returns:
            str: Path to the output GeoJSON(.gz) file.
        """
        suffix = ".geojson.gz" if compress else ".geojson"
        if filepath is None:
            tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            filepath = tmpfile.name
            tmpfile.close()
        else:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
        with get_ogr_datasource() as src_ds:
            layer: ogr.Layer = src_ds.ExecuteSQL(get_query_as_sql(self.query))
            field_name = "polygon"
            open_func = gzip.open if compress else open
            mode = 'wt'  # text mode with UTF-8 encoding
            with open_func(filepath, mode, encoding='utf-8') as f:
                f.write('{"type": "FeatureCollection", "features": [\n')
                first = True

                for feature in layer:
                    # geom = feature.GetGeomFieldRef(field_name)    # NOTE: Only useful if we want to use ExportToJson() instead of GetField()
                    geojson_feature = {
                        "type": "Feature",
                        "geometry": json.loads(feature.GetField(field_name)),    # NOTE: Could alternatively use geom.ExportToJson(), but this would require a modified query without AS_GeoJSON(). NOTE: potentially optimize using orjson.loads
                        "properties": feature.items()
                    }

                    if not first:
                        f.write(',\n')
                    else:
                        first = False

                    json.dump(geojson_feature, f)

                f.write('\n]}')

            print(f"GeoJSON written to: {filepath}")
            return filepath

    def get_all_annotations_as_feature_collection(self) -> bytes:
        """
        Returns all annotations as a byte string.

        Returns:
            bytes: The byte string representation of the annotations.
        """
        annotations = self.get_all_annotations()
        feature_collection = anns_to_feature_collection(annotations)
        return feature_collection


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
    
