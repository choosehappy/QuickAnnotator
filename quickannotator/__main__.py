from flask import Flask
from quickannotator.api import api_blueprint
import argparse
from waitress import serve
from quickannotator.config import config
from quickannotator.db import db




def serve_quickannotator(app):
    # NOTE: Will need to account for reverse proxy scenarios: https://docs.pylonsproject.org/projects/waitress/en/stable/reverse-proxy.html
    try:
        serve(app, host='0.0.0.0', port=config.getint('flask', 'port', fallback=5555),
               threads=config.getint('flask', 'threads', fallback=8))
        
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt")
    else:
        print("QA application terminated by user")

def serve_quickannotator_dev(app):
    app.run(debug=True, host='0.0.0.0', port=config.getint('flask', 'port', fallback=5555))


if __name__ == '__main__':

    app = Flask(__name__)
    app.register_blueprint(api_blueprint)
    app.config['RESTX_MASK_SWAGGER'] = False

    db.app = app
    db.init_app(app)
    db.create_all()
    db.engine.connect().execute('pragma journal_mode=wal;')

    # serve_quickannotator()
    serve_quickannotator_dev(app)
