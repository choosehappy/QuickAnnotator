from sqlalchemy.orm import Query
from quickannotator import constants
from quickannotator.db import Base, db_session, engine
from sqlalchemy import Table
import os
from datetime import datetime

from quickannotator.db.crud.image import get_image_by_id
from quickannotator.db.fsmanager import fsmanager

def create_dynamic_model(table_name, base=Base):
    class DynamicAnnotation(base):
        __tablename__ = table_name
        __table__ = Table(table_name, base.metadata, autoload_with=engine)

    return DynamicAnnotation


def build_annotation_table_name(image_id: int, annotation_class_id: int, is_gt: bool):
    gtpred = 'gt' if is_gt else 'pred'
    table_name = f"annotation_{image_id}_{annotation_class_id}_{gtpred}"
    return table_name


def build_export_filepath(image_id: int, annotation_class_id: int, is_gt: bool, extension: constants.ExportFormatExtensions, relative: bool, timestamp: datetime = None) -> str:
    timestamp = datetime.now() if timestamp is None else timestamp
        
    project_id = get_image_by_id(image_id).project_id
    save_path = fsmanager.nas_write.get_project_image_path(project_id, image_id, relative)

    table_name = build_annotation_table_name(image_id, annotation_class_id, is_gt)
    filename = f"{table_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.{extension.value}.gz"

    filepath = os.path.join(save_path, filename)
    return filepath


def get_query_as_sql(query: Query) -> str:
    """
    Returns the SQL query as a string.

    dialect allows us to avoid code splitting depending on the dialect. If not used, compile() will not use sqlite dialect functions including ScaleCoords
    """
    return query.statement.compile(compile_kwargs={"literal_binds": True}, dialect=db_session.bind.dialect).string

