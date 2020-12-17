# Imports:
import os
import logging

from sqlalchemy.ext.automap import automap_base

from flask import jsonify, current_app, send_from_directory
from flask_sqlalchemy import SQLAlchemy

from QA_worker import run_script

import QA_db
from QA_db import Job, JobidBase, set_job_status
from QA_config import config

# seconds to sleep before re-querying the server:
retry_seconds = config.getint('frontend', 'retry_seconds', fallback=20)

db = SQLAlchemy()
jobs_logger = logging.getLogger('jobs')


################################################################################
# Check if a job with this (command & parameters) is running or queued.
#
# We output that job. If the job does not exist or is in a "DONE"/"ERROR"
# state, we return None.
def getUnfinishedJob(project_name, command, imageid):
    # get the job:
    project_id = QA_db.get_project_id(project_name)
    current_app.logger.info(f'Checking if a job is free for project {project_id} ("{project_name}").')
    job = Job.query.filter_by(
        projId=project_id,
        cmd=command,
        imageId=imageid).filter(
        Job.status != "DONE").filter(
        Job.status != "ERROR").first()

    return job


################################################################################


################################################################################
# Call this function to update a job's status in the database:
def update_completed_job_status(result):
    retval, job_id = result

    # non-zero integer return values indicate an error
    status = "DONE"
    if isinstance(retval, int) and retval != 0:
        status = "ERROR"

    jobs_logger.info(f'Setting job status to {status}')
    set_job_status(job_id, status)


# If no callback has been assigned after an async job is run, call this function:
def worker_default_callback(result):
    jobs_logger.info('Default callback upon job completion called.')
    jobs_logger.info(f'Full result = {result}')
    update_completed_job_status(result)
    jobs_logger.info('Worker callback done.')


# This gets called once an async job is complete and updates the database status:
def error_default_callback(error):  # TODO update!! This is very important!
    jobs_logger.error(f'Worker ERROR callback upon job completion fail. {error}')


################################################################################


################################################################################
# Add this job to the database and start run it asynchronously.
#
# The whatToRun should be a function which takes in two arguments: arguments & jobId.
#
# project_id, command, and parameters define the job in the database.
#
# It will output the 202 html response code
# and a json request to check again in a few seconds.
def add_async_job(project_id, command, parameters, arguments, what_to_run, imageid=None, callback=None):
    # log message:
    current_app.logger.info(f"Adding {command} to thread pool.")

    # create a new queued job:
    new_job = Job(projId=project_id, imageId = imageid, cmd=command, status="QUEUE", params=str(arguments), retval="")
    db.session.add(new_job)
    db.session.commit()

    # --- make job table now as well as an endpoint to the DB -- should go into a function so that the other function  can use it as well

    jobtablename = f"jobid_{new_job.id}"
    meta = QA_db.db.metadata
    newjobtable = JobidBase.__table__.tometadata(meta, name=jobtablename)
    newjobtable.create(bind=QA_db.db.engine, checkfirst=True)

    Base = automap_base()
    Base.prepare(QA_db.db.engine, reflect=True)
    newtableobj = Base.classes[jobtablename]
    newtableobj.__tablename__ = jobtablename
    current_app.apimanager.create_api(newtableobj,
                                      methods=['GET', 'POST', 'DELETE', 'PUT'],
                                      url_prefix='/api/db',
                                      results_per_page=0, max_results_per_page=0)

    # for the whatToRun function, we will pass in a tuple containing
    # the arguments (which it must unpack itself), and the job id
    arguments_and_job = (arguments, new_job.id)

    # spin up a new thread and run the whatToRun function in that thread:
    current_app.logger.info(f'Running {command} via {what_to_run}:')
    QA_db._pool.apply_async(what_to_run, args=arguments_and_job,
                            callback=worker_default_callback if callback is None else callback,
                            error_callback=error_default_callback)

    # output the 202 response code and a message to retry:
    current_app.logger.info('Reporting to the browser that the job was submitted with HTML response code 202.')
    return jsonify(job=new_job.as_dict(), retry=retry_seconds), 202


################################################################################
# Run an external script (cmd) asynchronously.
#
# command_name is non-functional and just for
# identifying this command in the database.
#
# full_command should be a list of an external command
# and its arguments
def pool_run_script(project_name, command_name, full_command, imageid=None, callback=None):
    # check if the job is free:
    parameters = project_name  # <-- by convention for running scripts
    job = getUnfinishedJob(project_name, command_name, imageid)

    if job is None:
        project_id = QA_db.get_project_id(project_name)
        return add_async_job(project_id, command_name, parameters, full_command, run_script, imageid=imageid,
                             callback=callback)
    else:
        return jsonify(job=job.as_dict(), retry=retry_seconds), 409  # --job exists, return the job


################################################################################


################################################################################
# Output an image that will be calculated with function_name
# given a set of args and then stored at image_filename.
#
# parameters are used to help identify this job in the database.
#
# If the image exists, it will be output.
# If not, it will be calculated asynchronously.
def pool_get_image(project_name, command_name, full_command, image_filename, imageid=None, callback=None):
    current_app.logger.info(f'Getting image {image_filename} from project {project_name}.')

    # check if the image exists on disk:
    if not os.path.isfile(image_filename):

        current_app.logger.info(
            f'Image does not exist. Running function {command_name} with parameters {full_command}.')
        return pool_run_script(project_name, command_name, full_command, imageid=imageid, callback=callback)

    else:

        # This image exists and the job is done; output it to the frontend:
        folder, filename = os.path.split(image_filename)
        response = send_from_directory(folder, filename)

        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
################################################################################
