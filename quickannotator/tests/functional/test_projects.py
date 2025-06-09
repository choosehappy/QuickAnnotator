import pytest
from quickannotator.db.models import Project, Image, AnnotationClass, Tile
from quickannotator.db.crud.annotation import AnnotationStore

def test_delete_project(test_client, db_session, annotations_seed):
    """
    GIVEN a test client and an existing project
    WHEN the client deletes the project using a DELETE request
    THEN the response should have a status code of 204 and the project, along with its related data, should be removed from the database
    """

    # Arrange
    project_id = 1  # Assuming the project with ID 1 exists
    image_ids = [image.id for image in db_session.query(Image).filter(Image.project_id == project_id).all()]
    annotation_class_ids = [annotation_class.id for annotation_class in db_session.query(AnnotationClass).filter(AnnotationClass.project_id == project_id).all()]
    project = db_session.query(Project).get(project_id)

    params = {'project_id': project.id}

    # Act
    response = test_client.delete('/api/v1/project/', query_string=params)

    # Assert
    assert response.status_code == 204

    # Verify the project is deleted
    deleted_project = db_session.query(Project).get(project_id)
    assert deleted_project is None

    # Verify related images are deleted
    images = db_session.query(Image).filter(Image.project_id == project_id).all()
    assert len(images) == 0

    # Verify related annotation classes are deleted
    annotation_classes = db_session.query(AnnotationClass).filter(AnnotationClass.project_id == project_id).all()
    assert len(annotation_classes) == 0

    # Verify related tiles are deleted
    tiles = db_session.query(Tile).filter(
        Tile.image_id.in_(image_ids),
        Tile.annotation_class_id.in_(annotation_class_ids)
    ).all()
    assert len(tiles) == 0

    # Verify annotation tables are dropped
    for image_id in image_ids:
        for annotation_class_id in annotation_class_ids:
            try:
                AnnotationStore(image_id, annotation_class_id, is_gt=True, require_table_exists=True)
            except ValueError:
                # If the table does not exist, it raises a ValueError
                assert True, "Annotation table should not exist after project deletion"