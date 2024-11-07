import shutil
from flask import Flask
from flask_smorest import Api, Blueprint
import argparse
from waitress import serve
from quickannotator.config import config
from quickannotator.db import db, Project, Image, AnnotationClass, Notification, Tile, Setting, Annotation, SearchCache
from quickannotator.config import get_database_uri, get_database_path
from geoalchemy2 import load_spatialite
from sqlalchemy import event
import os
from quickannotator.api.v1 import annotation, project, image, annotation_class, notification, tile, setting, ray

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
    args = parser.parse_args()
    os.environ['SPATIALITE_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu/mod_spatialite.so'  # TODO: set with a function

    # ------------------------ APP SETUP ------------------------
    app = Flask(__name__)
    SearchCache.init_app(app)
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()

    # ------------------------ DB SETUP ------------------------
    if args.recreate_db:
        db_path = get_database_path()
        if os.path.exists(db_path):
            shutil.rmtree(db_path)

    models = [Project, Image, AnnotationClass, Notification, Tile, Setting]
    db.app = app
    db.init_app(app)
    with app.app_context():
        event.listen(db.engine, 'connect', load_spatialite)
        db.metadata.create_all(bind=db.engine, tables=[item.__table__ for item in models])


    # ------------------------ API SETUP ------------------------
    app.config["V1_API_TITLE"] = "QuickAnnotator_API"
    app.config["V1_API_VERSION"] = "v1"
    app.config["V1_OPENAPI_VERSION"] = "3.0.2"
    app.config["V1_OPENAPI_URL_PREFIX"] = "/api/v1"
    app.config["V1_OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["V1_OPENAPI_SWAGGER_UI_URL"] = "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.24.2/"
    api = Api(app, config_prefix="V1_", )
    prefix = app.config["V1_OPENAPI_URL_PREFIX"]
    api.register_blueprint(annotation.bp, url_prefix=prefix + "/annotation")
    api.register_blueprint(annotation_class.bp, url_prefix=prefix + "/class")
    api.register_blueprint(project.bp, url_prefix=prefix + "/project")
    api.register_blueprint(image.bp, url_prefix=prefix + "/image")
    api.register_blueprint(notification.bp, url_prefix=prefix + "/notification")
    api.register_blueprint(setting.bp, url_prefix=prefix + "/setting")
    api.register_blueprint(tile.bp, url_prefix=prefix + "/tile")
    api.register_blueprint(ray.bp, url_prefix=prefix + "/ray")

    # serve_quickannotator(app)
    serve_quickannotator_dev(app)
