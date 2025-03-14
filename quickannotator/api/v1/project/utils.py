from quickannotator.db import db_session
import quickannotator.db.models as models
from datetime import datetime

def add_project(name, description, is_dataset_large):
        project = models.Project(name=name,
                          description=description,
                          is_dataset_large=is_dataset_large,
                          datetime=datetime.now())
        db_session.add(project)