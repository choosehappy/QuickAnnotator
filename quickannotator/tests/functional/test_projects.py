import pytest
from quickannotator.db.models import Project, Image, AnnotationClass, Tile
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.crud.project import add_project
from quickannotator.db.crud.annotation_class import insert_annotation_class


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_project_with_classes(db_session, num_classes=2):
    """Create a project with `num_classes` annotation classes and return the project."""
    project = add_project(name="Stats Test Project", description="For stats tests", is_dataset_large=False)
    for i in range(num_classes):
        insert_annotation_class(
            project_id=project.id,
            name=f"Class {i}",
            color="#FF0000",
            work_mag=10,
            work_tilesize=2048,
        )
    db_session.commit()
    return project


# ---------------------------------------------------------------------------
# ProjectAnnotationStats  GET /<project_id>/annotations/stats/
# ---------------------------------------------------------------------------

def test_annotation_stats_group_by_annotation_class(test_client, db_session):
    """
    GIVEN a project with annotation classes
    WHEN GET /<project_id>/annotations/stats/?group_by=annotation_class
    THEN returns 200 with one entry per class, each containing group_id, group_label, and stats.count
    """
    project = _seed_project_with_classes(db_session, num_classes=2)

    response = test_client.get(
        f'/api/v1/project/{project.id}/annotations/stats/',
        query_string={'group_by': 'annotation_class'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    for item in data:
        assert 'group_id' in item
        assert 'group_label' in item
        assert 'stats' in item
        assert 'count' in item['stats']
        assert isinstance(item['stats']['count'], int)


def test_annotation_stats_group_by_image(test_client, db_session, seed):
    """
    GIVEN a project with images and annotation classes
    WHEN GET /<project_id>/annotations/stats/?group_by=image
    THEN returns 200 with one entry per image, each containing group_id, group_label, and stats.count
    """
    project_id = 1  # provided by seed fixture

    response = test_client.get(
        f'/api/v1/project/{project_id}/annotations/stats/',
        query_string={'group_by': 'image'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    for item in data:
        assert 'group_id' in item
        assert 'group_label' in item
        assert 'stats' in item
        assert 'count' in item['stats']
        assert isinstance(item['stats']['count'], int)


def test_annotation_stats_filter_by_annotation_class_ids(test_client, db_session):
    """
    GIVEN a project with 2 annotation classes
    WHEN GET /<project_id>/annotations/stats/ filtered to only one class id
    THEN returns 200 with exactly one entry matching that class
    """
    project = _seed_project_with_classes(db_session, num_classes=2)
    classes = db_session.query(AnnotationClass).filter(AnnotationClass.project_id == project.id).all()
    target_class = classes[0]

    response = test_client.get(
        f'/api/v1/project/{project.id}/annotations/stats/',
        query_string={'group_by': 'annotation_class', 'annotation_class_ids': str(target_class.id)}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['group_id'] == target_class.id
    assert data[0]['group_label'] == target_class.name


def test_annotation_stats_invalid_group_by(test_client, db_session):
    """
    GIVEN a project
    WHEN GET /<project_id>/annotations/stats/?group_by=invalid
    THEN returns 400
    """
    project = _seed_project_with_classes(db_session, num_classes=1)

    response = test_client.get(
        f'/api/v1/project/{project.id}/annotations/stats/',
        query_string={'group_by': 'invalid'}
    )

    assert response.status_code == 400


def test_annotation_stats_empty_project(test_client, db_session):
    """
    GIVEN a project with no annotation classes
    WHEN GET /<project_id>/annotations/stats/?group_by=annotation_class
    THEN returns 200 with an empty list
    """
    project = add_project(name="Empty Project", description="No classes", is_dataset_large=False)
    db_session.commit()

    response = test_client.get(
        f'/api/v1/project/{project.id}/annotations/stats/',
        query_string={'group_by': 'annotation_class'}
    )

    assert response.status_code == 200
    assert response.get_json() == []


# ---------------------------------------------------------------------------
# ProjectAnnotationClassStats  GET /<project_id>/annotation_class/stats
# ---------------------------------------------------------------------------

def test_annotation_class_stats(test_client, db_session):
    """
    GIVEN a project with 3 annotation classes
    WHEN GET /<project_id>/annotation_class/stats
    THEN returns 200 with stats.count == 3
    """
    project = _seed_project_with_classes(db_session, num_classes=3)

    response = test_client.get(f'/api/v1/project/{project.id}/annotation_class/stats')

    assert response.status_code == 200
    data = response.get_json()
    assert 'stats' in data
    assert 'count' in data['stats']
    assert data['stats']['count'] == 3


def test_annotation_class_stats_empty(test_client, db_session):
    """
    GIVEN a project with no annotation classes
    WHEN GET /<project_id>/annotation_class/stats
    THEN returns 200 with stats.count == 0
    """
    project = add_project(name="Empty Project", description="No classes", is_dataset_large=False)
    db_session.commit()

    response = test_client.get(f'/api/v1/project/{project.id}/annotation_class/stats')

    assert response.status_code == 200
    data = response.get_json()
    assert data['stats']['count'] == 0


# ---------------------------------------------------------------------------
# ProjectImageStats  GET /<project_id>/image/stats
# ---------------------------------------------------------------------------

def test_image_stats(test_client, db_session, seed):
    """
    GIVEN a project seeded with at least one image
    WHEN GET /<project_id>/image/stats
    THEN returns 200 with stats.count >= 1
    """
    project_id = 1  # provided by seed fixture

    response = test_client.get(f'/api/v1/project/{project_id}/image/stats')

    assert response.status_code == 200
    data = response.get_json()
    assert 'stats' in data
    assert 'count' in data['stats']
    assert data['stats']['count'] >= 1


def test_image_stats_empty(test_client, db_session):
    """
    GIVEN a project with no images
    WHEN GET /<project_id>/image/stats
    THEN returns 200 with stats.count == 0
    """
    project = add_project(name="No Images Project", description="No images", is_dataset_large=False)
    db_session.commit()

    response = test_client.get(f'/api/v1/project/{project.id}/image/stats')

    assert response.status_code == 200
    data = response.get_json()
    assert data['stats']['count'] == 0
