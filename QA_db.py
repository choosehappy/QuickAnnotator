from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Text
import sqlalchemy
import logging
from QA_config import get_database_uri
jobs_logger = logging.getLogger('jobs')

_pool = []

db = SQLAlchemy()


# Create Flask-SQLALchemy models
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(Text, nullable=False, unique=True)
    description = db.Column(db.Text, default="")
    date = db.Column(db.DateTime)
    train_ae_time = db.Column(db.DateTime)
    make_patches_time = db.Column(db.DateTime)
    iteration = db.Column(db.Integer, default=-1)
    embed_iteration = db.Column(db.Integer, default=-1)
    images = db.relationship('Image', backref='project', lazy=True)
    jobs = db.relationship('Job', backref='project', lazy=True)


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    projId = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.Text)
    path = db.Column(db.Text, unique=True)
    height = db.Column(db.Integer)
    width = db.Column(db.Integer)
    ppixel = db.Column(db.Integer, default=0)
    npixel = db.Column(db.Integer, default=0)
    nobjects = db.Column(db.Integer, default=0)
    date = db.Column(db.DateTime)
    rois = db.relationship('Roi', backref='image', lazy=True)
    make_patches_time = db.Column(db.DateTime)
    superpixel_time = db.Column(db.DateTime)
    superpixel_modelid = db.Column(db.Integer, default=-1)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Roi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imageId = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    name = db.Column(db.Text)
    path = db.Column(db.Text)
    testingROI = db.Column(db.Integer, default=-1)
    height = db.Column(db.Integer)
    width = db.Column(db.Integer)
    x = db.Column(db.Integer)
    y = db.Column(db.Integer)
    nobjects = db.Column(db.Integer, default=0)
    date = db.Column(db.DateTime)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    projId = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    imageId = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=True)
    cmd = db.Column(db.Text)
    params = db.Column(db.Text)
    status = db.Column(db.Text)
    retval = db.Column(db.Text)
    start_date = db.Column(db.DateTime, server_default=db.func.now())

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class JobidBase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.Text)
    procout = db.Column(db.Text)


# Remove all queued and running jobs from the database
def clear_stale_jobs():
    jobs_deleted = Job.query.filter_by(status='QUEUE').delete()
    jobs_deleted += Job.query.filter_by(status='RUNNING').delete()
    return jobs_deleted


def set_job_status(job_id, status, retval = ""):
    if job_id:
        engine = sqlalchemy.create_engine(get_database_uri())
        engine.connect().execute(f"update job set status= :status, retval = :retval where id={job_id}", status=status, retval = retval)
        engine.dispose()
        jobs_logger.info(f'Job {job_id} set to status "{status}".')


# Output the project id from the database for a given name:
def get_project_id(project_name):
    return Project.query.filter_by(name=project_name).first().id


# Output the index of the latest trained ai
def get_latest_modelid(project_name):
    # pull the last training iteration from the database
    selected_proj = db.session.query(Project).filter_by(name=project_name).first()
    iteration = int(selected_proj.iteration)

    # count backwards until we find a trained model for the given index

    # --- AJ: Lets comment this out for now to see if/when it breaks. with the improved callback, we should
    # never be in this situation now and this code is more of a hack than a solution

    # for model_id in range(iteration, -2, -1):
    #     model_path = f"./projects/{project_name}/models/{model_id}/best_model.pth"
    #     model_exists = os.path.exists(model_path)
    #     if (model_exists):
    #         break

    # output the id
    return iteration

