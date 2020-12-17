import logging
import subprocess
import sys
import threading

import sqlalchemy

from QA_config import get_database_uri
from QA_db import set_job_status

jobs_logger = logging.getLogger('jobs')


################################################################################
# Run an external command and block until it's finished:
def run_script(external_command, job_id):

    # get the thread's id:
    command_id = threading.get_ident()
    set_job_status(job_id, "RUNNING")

    # say the job is running:
    engine = sqlalchemy.create_engine(get_database_uri())

    jobs_logger.info(f'Running command {command_id}: {external_command}')

    # from https://stackoverflow.com/a/18422264
    process = subprocess.Popen(external_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # display the output:
    for line in iter(process.stdout.readline, b''):
        output = line.strip().decode('utf-8')
        jobs_logger.debug(output)
        engine.connect().execute(f"insert into jobid_{job_id} (timestamp,procout) values  (datetime('now'), :output);", output = output)

    # https://stackoverflow.com/a/39477756
    jobs_logger.info("Waiting for the job and then getting stdout and stderr:")
    stdout, stderr = process.communicate()
    jobs_logger.info("Closing stdout:")
    process.stdout.close()

    # check if there were any errors:
    stderr = stderr.strip().decode('utf-8')
    if stderr != "":
        jobs_logger.error(f'stderr = {stderr}')

    jobs_logger.info("Polling for completion:")
    return_value = process.poll()
    jobs_logger.info(f'Return value = {return_value}')
    engine.connect().execute(f"insert into jobid_{job_id} (timestamp,procout) values  (datetime('now'), :retval);",retval = f"Return value: {return_value}")
    engine.dispose()

    return return_value, job_id  # <-- output the command's output


# Run a python function and block until it's finished.
# Code isn't currently used and thus hasn't been validated since 4/2020. use with caution
# def run_function(function_and_arguments, job_id):
#
#     jobs_logger.info(f'Running function {function_and_arguments} as job {job_id}.')
#     set_job_status(job_id, "RUNNING")
#
#     function = function_and_arguments[0]  # <-- extract the function to run
#     arguments = function_and_arguments[1]  # <-- extract the arguments to pass to it
#     arguments += (job_id,)
#
#     jobs_logger.info('Running function = {}'.format(function))
#     jobs_logger.info('Aguments = {}'.format(arguments))
#     return_value = globals()[function](*arguments)  # <-- run the function
#     return return_value, job_id  # <-- output the result with the job id
# ################################################################################
