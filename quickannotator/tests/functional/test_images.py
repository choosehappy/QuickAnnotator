import pytest
from quickannotator.db.models import Image, AnnotationClass, Tile
from quickannotator.db.crud.annotation import AnnotationStore


def test_get_image_metadata(test_client, seed):
    """
    GIVEN a test client and an existing image
    WHEN the client requests the metadata of the image using a GET request
    THEN the response should have a status code of 200 and the returned metadata should match the expected metadata
    """

    # Arrange
    image_id = 1  # Assuming an image with ID 1 exists in the seed data

    # Act
    response = test_client.get(f'/api/v1/image/{image_id}/metadata')

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert 'mpp' in data  # Check that the metadata contains the 'mpp' field
    assert data['mpp'] == pytest.approx(0.2261727054779029)  # Check that the MPP value matches the expected value approximately


def test_delete_image(test_client, db_session, annotations_seed):
    """
    GIVEN a test client and an existing image
    WHEN the client deletes the image using a DELETE request
    THEN the response should have a status code of 204 and the image, along with its related data, should be removed from the database
    """

    # Arrange
    image_id = 1  # Assuming the image with ID 1 exists
    annotation_class_ids = [annotation_class.id for annotation_class in db_session.query(AnnotationClass).filter(AnnotationClass.project_id == 1).all()]
    image = db_session.query(Image).get(image_id)

    params = {'image_id': image.id}

    # Act
    response = test_client.delete('/api/v1/image/', query_string=params)

    # Assert
    assert response.status_code == 204

    # Verify the image is deleted
    deleted_image = db_session.query(Image).get(image_id)
    assert deleted_image is None

    # Verify related tiles are deleted
    tiles = db_session.query(Tile).filter(Tile.image_id == image_id).all()
    assert len(tiles) == 0

    # Verify annotation tables are dropped
    for annotation_class_id in annotation_class_ids:
        try:
            AnnotationStore(image_id, annotation_class_id, is_gt=True, require_table_exists=True)
        except ValueError:
            # If the table does not exist, it raises a ValueError
            assert True, "Annotation table should not exist after image deletion"


