import quickannotator.db.models as db_models
from quickannotator.db import db_session


def add_project(name, description, is_dataset_large):
        project = db_models.Project(name=name,
                          description=description,
                          is_dataset_large=is_dataset_large)
        db_session.add(project)

def get_project_by_id(project_id: int) -> db_models.Project:
    return db_session.query(db_models.Project).get(project_id)


def delete_projects(project_ids: list[int] | int):
    """
    Delete projects by their IDs.
    Args:
        project_ids (list[int] | int): A list of project IDs or a single project ID to delete.
    """
    if isinstance(project_ids, int):
        project_ids = [project_ids]
    
    db_session.query(db_models.Project).filter(db_models.Project.id.in_(project_ids)).delete(synchronize_session=False)
    db_session.commit()