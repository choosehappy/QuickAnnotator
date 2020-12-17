import os
import shutil
import logging
from logging import config
from multiprocessing import Pool

from flask import Flask
from flask_restless import APIManager, ProcessingException

import QA_db
from QA_api import api,delete_image
from QA_config import config, get_database_uri
from QA_db import db, Image, Project, Roi, Job
from QA_html import html


def add_project(**kw):
    projectid = kw['result']['name']

    # Check if the project folder exists
    if not os.path.isdir("projects"):
        os.mkdir("projects")

    if not os.path.isdir(os.path.join("projects", projectid)):
        # Create new project under root, add sub-folders
        os.mkdir(os.path.join("projects", projectid))

        os.mkdir(os.path.join("projects", projectid, "models"))
        os.mkdir(os.path.join("projects", projectid, "pred"))
        os.mkdir(os.path.join("projects", projectid, "mask"))
        os.mkdir(os.path.join("projects", projectid, "patches"))
        os.mkdir(os.path.join("projects", projectid, "roi"))
        os.mkdir(os.path.join("projects", projectid, "roi_mask"))
        os.mkdir(os.path.join("projects", projectid, "superpixels"))
        os.mkdir(os.path.join("projects", projectid, "superpixels_boundary"))

    return kw


def delete_project(instance_id=None, **kw):  # should really be a postprocess but no instance ID is available
    # Delete all images in the project, this function removes the relational foreign keys as well
    proj = Project.query.filter_by(id=instance_id).first()
    
    selected_images = db.session.query(Image).filter_by(projId=proj.id)
    for selected_image in selected_images:
        delete_image(proj.name, selected_image.name)

    #delete jobs
    selected_Jobs = db.session.query(Job).filter_by(projId=proj.id)
    selected_Jobs.delete()

    # Check if the project folder exists
    shutil.rmtree(os.path.join("projects", proj.name), ignore_errors=True)

    pass


# For the preprocessor to raise an exception if a duplicate project name is posted.
def check_existing_project(data):
    project_name = data['name']
    proj = Project.query.filter_by(name=project_name).first()
    if proj is not None:
        raise ProcessingException(description=f'Project {project_name} already exists.', code=400)


# Create the Flask-Restless API manager
app = Flask(__name__)
app.debug = True
app.logger_name='flask'
app.register_blueprint(api)
app.register_blueprint(html)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = config.getboolean('sqlalchemy', 'echo', fallback=False)

APP_ROOT = os.path.dirname(os.path.abspath('__file__'))

if __name__ == '__main__': #This seems like the correct place to do this

    # load logging config
    logging.config.fileConfig('logging.ini')
    
    app.logger.info('Initializing database')
    
    db.app = app
    db.init_app(app)
    db.create_all()
    db.engine.connect().execute('pragma journal_mode=wal;')

    if config.getboolean('sqlalchemy', 'delete_old_jobs_at_start', fallback=True):
        jobid_tables = db.session.execute("SELECT name FROM sqlite_master WHERE type='table' and name like 'jobid_%' ORDER BY name").fetchall()
        for jobid_table in jobid_tables:
            app.logger.info(f'Dropping jobid_table {jobid_table[0]}')
            db.session.execute(f"DROP TABLE IF EXISTS {jobid_table[0]}")

        db.session.commit()



    # ----
    app.logger.info('Clearing stale jobs')
    if config.getboolean('flask', 'clear_stale_jobs_at_start', fallback=True):
        njobs = QA_db.clear_stale_jobs()  # <-- clear old queued jobs from last session
        db.session.commit()
        app.logger.info(f'Deleted {njobs} queued jobs.')

    # ----
    app.apimanager = APIManager(app, flask_sqlalchemy_db=db)

    # Create API endpoints, which will be available at /api/<tablename> by default
    app.apimanager.create_api(Project, methods=['GET', 'POST', 'DELETE', 'PUT'], url_prefix='/api/db',
                       results_per_page=0, max_results_per_page=0,
                       preprocessors={'DELETE_SINGLE': [delete_project], 'POST': [check_existing_project]},
                       postprocessors={'POST': [add_project]})

    app.apimanager.create_api(Image, methods=['GET', 'POST', 'DELETE', 'PUT'], url_prefix='/api/db',
                       results_per_page=0, max_results_per_page=0,)
    app.apimanager.create_api(Roi, methods=['GET', 'POST', 'DELETE', 'PUT'], url_prefix='/api/db',
                       results_per_page=0, max_results_per_page=0,)
    app.apimanager.create_api(Job, methods=['GET', 'POST', 'DELETE', 'PUT'], url_prefix='/api/db',
                       results_per_page=0, max_results_per_page=0,)

    app.logger.info('Starting up worker pool.')
    QA_db._pool = Pool(processes=config.getint('pooling', 'npoolthread', fallback=4))
    app.run(host='0.0.0.0', port=config.getint('flask', 'port', fallback=5555), debug=config.getboolean('flask', 'debug', fallback = False))
    QA_db._pool.close()
    QA_db._pool.join()
