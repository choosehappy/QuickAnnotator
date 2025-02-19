import os

os.environ['TESTING'] = 'false'  # need to set this before importing the db module

from quickannotator.api import init_api
import shutil
from flask import Flask
from flask_smorest import Blueprint
import argparse
from waitress import serve
from quickannotator.config import config
from quickannotator.config import get_database_uri, get_database_path, get_ray_dashboard_host, get_ray_dashboard_port, get_api_version
from geoalchemy2 import load_spatialite
import ray
from quickannotator.db.models import Annotation, AnnotationClass, Image, Notification, Project, Setting, Tile
from quickannotator.db import init_db, db_session

def serve_quickannotator(app):
    # NOTE: Will need to account for reverse proxy scenarios: https://docs.pylonsproject.org/projects/waitress/en/stable/reverse-proxy.html
    try:
        serve(app, host='0.0.0.0', port=config.getint('flask', 'port', fallback=5000),
               threads=config.getint('flask', 'threads', fallback=8))
        
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt")
    else:
        print("QA application terminated by user")

def serve_quickannotator_dev(app):
    app.run(debug=True, host='0.0.0.0', port=config.getint('flask', 'port', fallback=5000), threaded=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=config.getint('flask', 'port', fallback=5000))
    parser.add_argument('-r', '--recreate_db',  action='store_true', default=False,
        help="Restore QuickAnnotator to its factory state. WARNING: all projects and respective data will be deleted.")
    parser.add_argument('-a', '--cluster_address', type=str, default=None)
    args = parser.parse_args()
    os.environ['SPATIALITE_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu/mod_spatialite.so'  # TODO: set with a function


    # ------------------------ APP SETUP ------------------------
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()

    # ------------------------ DB SETUP ------------------------
    if args.recreate_db:
        db_path = get_database_path()
        if os.path.exists(db_path):
            shutil.rmtree(db_path)

    init_db()

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            db_session.rollback()
        else:
            try:
                db_session.commit()
            except Exception:
                db_session.rollback()
                raise
        db_session.remove()
        

    # ------------------------ RAY SETUP ------------------------
    print(f"Connecting to Ray cluster")
    context = ray.init(address=args.cluster_address, dashboard_host=get_ray_dashboard_host(), dashboard_port=get_ray_dashboard_port())
    
    print(f"Ray dashboard available at {context.dashboard_url}")

    # ------------------------ API SETUP ------------------------
    init_api(app, get_api_version())

    # serve_quickannotator(app)
    serve_quickannotator_dev(app)
