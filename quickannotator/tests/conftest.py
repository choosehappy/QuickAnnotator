import os
import pytest
from flask import Flask
from quickannotator.db import init_db, drop_db, db_session, Base, get_session
from quickannotator.api import init_api
from quickannotator.config import get_database_uri, get_api_version
from quickannotator.db import models
from quickannotator.api.v1.project.utils import add_project
from quickannotator.api.v1.image.utils import add_image_by_path, get_image_by_id
from quickannotator.api.v1.annotation_class.helper import insert_annotation_class
from quickannotator.api.v1.utils.shared_crud import insert_new_annotation
from quickannotator.api.v1.tile.helper import upsert_tile
from quickannotator.constants import TileStatus
from shapely.geometry import Polygon
from quickannotator.api.v1.tile.helper import upsert_tile
from quickannotator.api.v1.annotation.helper import create_annotation_table
from quickannotator.api.v1.utils.coordinate_space import TileSpace
from quickannotator.api.v1.utils.coordinate_space import get_tilespace
import quickannotator.constants as constants


@pytest.fixture(scope='module')
def test_client():
    # Set the Testing configuration prior to creating the Flask application
    app = Flask(__name__)
    
    # Configure the in-memory database
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    init_api(app, get_api_version())

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

@pytest.fixture(scope="function")
def db_session():

    init_db()

    try:
        with get_session() as db_session:
            yield db_session
    finally:
        drop_db()

@pytest.fixture(scope="function")
def seed(db_session):   # here db_session is the fixture
    # Add a project
    add_project(name="Test Project", description="A test project", is_dataset_large=False)
    
    # Add an image
    add_image_by_path(
                    project_id=1,
                    full_path="quickannotator/data/test_ndpi/13_266069_040_003 L02 PAS.ndpi"    # TODO: add test data
                    )
    
    # Add an annotation class
    insert_annotation_class(
                        project_id=None,
                        name="Tissue Mask",
                        color="black",
                        work_mag=1.25,
                        work_tilesize=2048,
                        dl_model_objectref=None)
    
    # Add a second annotation class
    insert_annotation_class(
                        project_id=1,
                        name="Fake Class",
                        color="red",
                        work_mag=10,
                        work_tilesize=2048,
                        dl_model_objectref=None)

    # Add a tile
    upsert_tile(
        annotation_class_id=2,
        image_id=1,
        tile_id=0,
        seen=TileStatus.UNSEEN,
        hasgt=False
    )

    db_session.commit()

@pytest.fixture(scope="function")
def annotations_seed(db_session, seed, fake_ann_class_tilespace, mask_tilespace):
    image_id = 1
    annotation_class_id = 2
    is_gt = True
    tilesize = 2048

    # Create the mask annotation table
    create_annotation_table(image_id, constants.MASK_CLASS_ID, is_gt=True)

    # Create the annotation table
    create_annotation_table(image_id, annotation_class_id, is_gt=True)

    # Create the prediction table
    create_annotation_table(image_id, annotation_class_id, is_gt=False)

    # Insert a mask annotation which envelopes all annotations
    mask_poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    tid = mask_tilespace.point_to_tileid(mask_poly.centroid.x, mask_poly.centroid.y)
    insert_new_annotation(image_id, constants.MASK_CLASS_ID, True, 0, mask_poly)
    upsert_tile(constants.MASK_CLASS_ID, image_id, tid, hasgt=True)

    for i in range(10):
        # Create a simple square polygon
        poly = Polygon([(i, i), (i + 1, i), (i + 1, i + 1), (i, i + 1), (i, i)])
        
        # Calculate the tile_id
        tile_id = fake_ann_class_tilespace.point_to_tileid(poly.centroid.x, poly.centroid.y)
        
        # Insert the annotation
        insert_new_annotation(image_id, annotation_class_id, True, tile_id, poly)

        # Also insert as prediction
        insert_new_annotation(image_id, annotation_class_id, False, tile_id, poly)
        
        # Upsert the tile
        upsert_tile(annotation_class_id, image_id, tile_id, hasgt=True)

    db_session.commit()

def assert_geojson_equal(geojson1, geojson2):
    """
    Custom assertion to compare two geojson objects for equality.
    """
    assert geojson1['type'] == geojson2['type'], f"Types do not match: {geojson1['type']} != {geojson2['type']}"
    assert geojson1['coordinates'] == geojson2['coordinates'], f"Coordinates do not match: {geojson1['coordinates']} != {geojson2['coordinates']}"


@pytest.fixture
def fake_ann_class_tilespace(seed):
    image_id = 1
    annotation_class_id = 2

    tilespace = get_tilespace(image_id=image_id, annotation_class_id=annotation_class_id)
    return tilespace

@pytest.fixture
def mask_tilespace(seed):
    image_id = 1
    annotation_class_id = 1

    tilespace = get_tilespace(image_id=image_id, annotation_class_id=annotation_class_id)
    return tilespace