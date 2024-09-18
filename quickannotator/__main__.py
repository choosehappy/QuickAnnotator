from flask import Flask
from quickannotator.api import api_blueprint
import argparse
from waitress import serve
from quickannotator.config import config




def run_quickannotator():
    # NOTE: Will need to account for reverse proxy scenarios: https://docs.pylonsproject.org/projects/waitress/en/stable/reverse-proxy.html

    app = Flask(__name__)
    app.register_blueprint(api_blueprint)
    try:
        serve(app, host='0.0.0.0', port=config.getint('flask', 'port', fallback=5555),
               threads=config.getint('flask', 'threads', fallback=8))
        
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt")
    else:
        print("QA application terminated by user")

def run_quickannotator_dev():
    app = Flask(__name__)
    app.register_blueprint(api_blueprint)
    app.config['RESTX_MASK_SWAGGER'] = False
    app.run(debug=True, host='0.0.0.0', port=config.getint('flask', 'port', fallback=5555))
    


if __name__ == '__main__':
    # run_quickannotator()
    run_quickannotator_dev()