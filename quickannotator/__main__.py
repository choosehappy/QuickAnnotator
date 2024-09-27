from flask import Flask
from quickannotator.api import api_blueprint
import argparse
from waitress import serve
from quickannotator.config import config
from quickannotator.db import db, Project, Image, AnnotationClass, Notification, SearchCache
from quickannotator.config import get_database_uri


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
    app.run(debug=True, host='0.0.0.0', port=config.getint('flask', 'port', fallback=5000))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=config.getint('flask', 'port', fallback=5000))
    parser.add_argument('--factory_reset', action='store_true', default=False,
        help="Restore QuickAnnotator to its factory state. WARNING: all projects and respective data will be deleted.")

    app = Flask(__name__)
    app.register_blueprint(api_blueprint)
    app.config['RESTX_MASK_SWAGGER'] = False
    # app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['CACHE_TYPE'] = "SimpleCache"
    SearchCache.init_app(app)

    models = [
        Project, Image, AnnotationClass, Notification
    ]
    db.app = app
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[item.__table__ for item in models])
    # serve_quickannotator(app)
    serve_quickannotator_dev(app)
