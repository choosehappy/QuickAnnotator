import os
import pytest
from flask import Flask
os.environ['TESTING'] = 'true'
from quickannotator.db import init_db, db_session
from quickannotator.api import init_api
from quickannotator.config import get_database_uri, get_api_version

@pytest.fixture(scope='module')
def test_client():
    # Set the Testing configuration prior to creating the Flask application
    app = Flask(__name__)
    
    # Configure the in-memory database
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    init_api(app, get_api_version())
    # Initialize the database
    with app.app_context():
        init_db()

    # Create a test client using the Flask application configured for testing
    with app.test_client() as testing_client:
        # Establish an application context
        with app.app_context():
            yield testing_client  # this is where the testing happens!

    # Teardown the database session
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
