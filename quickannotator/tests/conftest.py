import os
import pytest
from flask import Flask
from quickannotator.db import init_db, drop_db, db_session, get_session
from quickannotator.api import init_api
from quickannotator.config import get_database_uri, get_api_version
from quickannotator.db import models
from quickannotator.db.crud.project import add_project
from quickannotator.db.crud.image import add_image_by_path
from quickannotator.db.crud.annotation_class import insert_annotation_class
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.tile import TileStore, TileStoreFactory
from quickannotator.constants import TileStatus
from shapely.geometry import Polygon
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
    # This image has a base magnification of 40x. The dimensions are 150784x71936 pixels.
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
                        )
    
    # Add a second annotation class
    insert_annotation_class(
                        project_id=1,
                        name="Fake Class",
                        color="red",
                        work_mag=10,
                        work_tilesize=2048, # At base (40x) magnification, this is 2048 * 40 / 10 = 8192 pixels
                        )

    # Add a tile
    tilestore: TileStore = TileStoreFactory.get_tilestore()
    tilestore.upsert_gt_tiles(
        annotation_class_id=2,
        image_id=1,
        tile_ids=[0]
    )

    db_session.commit()

@pytest.fixture(scope="function")
def tissue_mask_seed(db_session, seed):
    image_id = 1
    annotation_class_id = 1

    # Create the mask annotation table
    mask_store = AnnotationStore(image_id, annotation_class_id, in_work_mag=False, is_gt=True, create_table=True)

    # Insert a mask annotation which envelopes all annotations
    minx, miny, maxx, maxy = 0, 0, 10000, 10000
    mask_poly = Polygon([(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy), (minx, miny)])
    mask_store.insert_annotations([mask_poly])

    db_session.commit()

@pytest.fixture(scope="module")
def polygons():
    num_annotations = 10
    minx, miny, maxx, maxy = 0, 0, 50000, 50000
    step = (maxx - minx) // num_annotations
    polygons = []
    for i in range(num_annotations):
        x_start = minx + i * step
        y_start = miny + i * step
        polygon = Polygon([
            (x_start, y_start),
            (x_start + step, y_start),
            (x_start + step, y_start + step),
            (x_start, y_start + step),
            (x_start, y_start)
        ])
        polygons.append(polygon)
    return polygons

@pytest.fixture(scope="function")
def annotations_seed(db_session, tissue_mask_seed, polygons):
    image_id = 1
    annotation_class_id = 2

    # Create the annotation table
    annotation_store = AnnotationStore(image_id, annotation_class_id, is_gt=True, in_work_mag=False, create_table=True)

    # Create the prediction table
    prediction_store = AnnotationStore(image_id, annotation_class_id, is_gt=False, in_work_mag=False, create_table=True)

    # Insert the annotations
    annotation_store.insert_annotations(polygons)

    # Also insert as predictions
    prediction_store.insert_annotations(polygons)

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