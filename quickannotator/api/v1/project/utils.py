from quickannotator.db import db_session
import quickannotator.db.models as models

def add_project(name, description, is_dataset_large):
        project = models.Project(name=name,
                          description=description,
                          is_dataset_large=is_dataset_large)
        db_session.add(project)