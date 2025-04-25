import quickannotator.db.models as db_models
from quickannotator.db import db_session


def add_project(name, description, is_dataset_large):
        project = db_models.Project(name=name,
                          description=description,
                          is_dataset_large=is_dataset_large)
        db_session.add(project)

def get_project_by_id(project_id: int) -> db_models.Project:
    return db_session.query(db_models.Project).get(project_id)

