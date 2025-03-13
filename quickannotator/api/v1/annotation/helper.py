import quickannotator.db as qadb
from sqlalchemy import func, select, text, MetaData, Table, insert
from sqlalchemy.orm import aliased, Session, Query
from typing import List
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import DateTime
import quickannotator.db.models as models
from quickannotator.db import db_session
from quickannotator.api.v1.utils.shared_crud import get_annotation_query
from quickannotator.api.v1.utils.coordinate_space import base_to_work_scaling_factor
from quickannotator.db.utils import build_annotation_table_name, create_dynamic_model
from shapely.geometry import Polygon
import geojson
from shapely.affinity import scale
from shapely.geometry.base import BaseGeometry
from datetime import datetime


Base = declarative_base()

class AnnotationStore:
    def __init__(self, image_id: int, annotation_class_id: int, is_gt: bool, in_work_mag=True):
        """
        Initializes the annotation helper with the given parameters.

        Args:
            image_id (int): The ID of the image.
            annotation_class_id (int): The ID of the annotation class.
            is_gt (bool): A flag indicating whether the annotation is ground truth.
            in_work_mag (bool, optional): If True, all input and output polygons are in working magnification. Defaults to True. 
                If False, all input and output polygons are in base magnification.


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
        self.model = create_dynamic_model(build_annotation_table_name(image_id, annotation_class_id, is_gt))
        self.scaling_factor = 1.0 if in_work_mag else base_to_work_scaling_factor(image_id, annotation_class_id)

    # CREATE
    def insert_annotations(self, polygons: List[BaseGeometry]):
        new_annotations = []
        for polygon in polygons:
            scaled_polygon = self._scale_polygon(polygon, self.scaling_factor)
            new_annotations.append({
                "image_id": self.image_id,
                "annotation_class_id": self.annotation_class_id,
                "isgt": self.is_gt,
                "tile_id": None,  # Ensure correct value
                "centroid": scaled_polygon.centroid.wkt,
                "polygon": scaled_polygon.wkt,
                "area": scaled_polygon.area,
                "custom_metrics": {},  # Add appropriate custom metrics if needed
                "datetime": datetime.now()
            })
        
        stmt = insert(self.model).returning(self.model).values(new_annotations)
        result = db_session.scalars(stmt).all()
        db_session.commit()
        return result
    

    # READ
    def get_annotation_by_id(self, annotation_id: int) -> models.Annotation:
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter_by(id=annotation_id).first()
        return result

    def get_annotations_for_tiles(self, tile_ids: List[int]) -> List[models.Annotation]:
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter(self.model.tile_id.in_(tile_ids)).all()
        return result

    def get_annotations_within_poly(self, polygon: geojson.Polygon) -> List[models.Annotation]:
        shapely_polygon = Polygon(polygon['coordinates'][0])
        scaled_polygon = self._scale_polygon(shapely_polygon, self.scaling_factor)
        # NOTE: Sqlite may not use the spatial index here.
        result = get_annotation_query(self.model, 1/self.scaling_factor).filter(func.ST_Intersects(self.model.polygon, scaled_polygon.wkt)).all()
        return result

    # DELETE
    def delete_all_annotations(self):
        db_session.query(self.model).delete()

    # MISC
    def create_annotation_table(self):
        table = self.model.__table__.to_metadata(Base.metadata, name=self.model.__tablename__)
        Base.metadata.create_all(bind=db_session.bind, tables=[table])
    
    @staticmethod
    def _scale_polygon(polygon: BaseGeometry, scaling_factor: float) -> BaseGeometry:   # Added for safety - I've forgotten the origin param several times.
        return scale(polygon, xfact=scaling_factor, yfact=scaling_factor, origin=(0, 0))


    

# def annotations_within_bbox(table, x1, y1, x2, y2):
#     envelope = func.BuildMbr(x1, y1, x2, y2)
#     # Right now we are selecting by centroid and not polygon.
#     stmt = table.select().where(func.ST_Intersects(table.c.centroid, envelope))
#     result = db_session.execute(stmt).fetchall()
#     return result


# def annotations_within_bbox_spatial(table_name: str, x1: float, y1: float, x2: float, y2: float) -> List[models.Annotation]:
#     stmt = text(f'''
#         SELECT ROWID, AsGeoJSON(centroid) as centroid, area, AsGeoJSON(polygon) as polygon, custom_metrics, datetime, annotation_class_id
#         FROM "{table_name}"
#         WHERE "{table_name}".ROWID IN (
#             SELECT ROWID
#             FROM SpatialIndex
#             WHERE f_table_name = "{table_name}"
#             AND f_geometry_column = 'centroid'
#             AND search_frame = BuildMbr({x1}, {y1}, {x2}, {y2})
#         )
#     ''').columns(datetime=DateTime())
    
#     result = db_session.execute(stmt).fetchall()
#     return result

# def count_annotations_within_bbox(table, x1, y1, x2, y2):
#     envelope = func.BuildMbr(x1, y1, x2, y2)
#     stmt = select(func.count()).where(func.ST_Intersects(table.c.centroid, envelope))
#     # stmt = table.select([func.count()]).where(func.ST_Intersects(table.c.centroid, envelope))

#     result = db_session.execute(stmt).scalar()
#     return result

# def retrieve_annotation_table(image_id: int, annotation_class_id: int, is_gt: bool) -> Table:
#     table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)

#     return Table(table_name, qadb.db.metadata, autoload_with=db_session.bind)
