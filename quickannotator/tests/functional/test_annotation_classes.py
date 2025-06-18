import pytest
from quickannotator.db.crud.annotation import AnnotationStore
from quickannotator.db.models import AnnotationClass, Tile, Annotation

def test_get_annotation_class(test_client, db_session):
    """
    GIVEN a test client and an existing annotation class
    WHEN the client requests the annotation class using a GET request
    THEN the response should have a status code of 200 and the returned data should match the annotation class
    """

    # Arrange
    annotation_class = AnnotationClass(project_id=1, name="Test Class", color="#FFFFFF", work_mag=10, work_tilesize=2048)
    db_session.add(annotation_class)
    db_session.commit()

    params = {'annotation_class_id': annotation_class.id}

    # Act
    response = test_client.get('/api/v1/class/', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == annotation_class.id
    assert data['name'] == annotation_class.name
    assert data['color'] == annotation_class.color
    assert data['work_mag'] == annotation_class.work_mag
    assert data['work_tilesize'] == annotation_class.work_tilesize


def test_post_annotation_class(test_client, db_session, seed):
    """
    GIVEN a test client and new annotation class data
    WHEN the client creates the annotation class using a POST request
    THEN the response should have a status code of 201 and the annotation class should be added to the database
    """

    # Arrange
    params = {
        'project_id': 1,
        'name': "New Class",
        'color': "#000000",
        'work_mag': 20,
        'tile_size': 2048
    }

    # Act
    response = test_client.post('/api/v1/class/', query_string=params)

    # Assert
    assert response.status_code == 201
    data = response.get_json()
    assert data['id'] is not None
    assert data['name'] == params['name']
    assert data['color'] == params['color']
    assert data['work_mag'] == params['work_mag']
    assert data['work_tilesize'] == params['tile_size']

    # Verify in the database
    annotation_class = db_session.query(AnnotationClass).get(data['id'])
    assert annotation_class is not None
    assert annotation_class.name == params['name']
    assert annotation_class.color == params['color']
    assert annotation_class.work_mag == params['work_mag']
    assert annotation_class.work_tilesize == params['tile_size']


def test_put_annotation_class(test_client, db_session):
    """
    GIVEN a test client and an existing annotation class
    WHEN the client updates the annotation class using a PUT request
    THEN the response should have a status code of 201 and the annotation class should be updated in the database
    """

    # Arrange
    annotation_class = AnnotationClass(project_id=1, name="Old Class", color="#123456", work_mag=15, work_tilesize=2048)
    db_session.add(annotation_class)
    db_session.commit()

    params = {
        'annotation_class_id': annotation_class.id,
        'name': "Updated Class",
        'color': "#654321",
    }

    # Act
    response = test_client.put('/api/v1/class/', query_string=params)

    # Assert
    assert response.status_code == 201

    # Verify in the database
    db_session.refresh(annotation_class)
    assert annotation_class.name == params['name']
    assert annotation_class.color == params['color']

# TODO: How to isolate file system within the test environment?
# def test_delete_annotation_class(test_client, db_session, annotations_seed):
#     """
#     GIVEN a test client and an existing annotation class
#     WHEN the client deletes the annotation class using a DELETE request
#     THEN the response should have a status code of 204 and the annotation class, along with its related tiles and annotations, should be removed from the database
#     """

#     # Arrange
#     annotation_class_id = 2
#     image_id = 1

#     annotation_class = db_session.query(AnnotationClass).get(annotation_class_id)

#     params = {'annotation_class_id': annotation_class.id}

#     # Act
#     response = test_client.delete('/api/v1/class/', query_string=params)

#     # Assert
#     assert response.status_code == 204

#     # Verify in the database
#     deleted_class = db_session.query(AnnotationClass).get(annotation_class_id)
#     assert deleted_class is None

#     # Verify related tiles are deleted
#     tiles = db_session.query(Tile).filter(Tile.annotation_class_id == annotation_class_id).all()
#     assert len(tiles) == 0

#     # Verify the annotation table is dropped
#     try:
#         AnnotationStore(image_id, annotation_class_id, is_gt=True, require_table_exists=True)
#     except ValueError:
#         # If the table does not exist, it raises a ValueError
#         assert True, "Annotation table should not exist after deletion"
    


def test_delete_non_existent_annotation_class(test_client, db_session, annotations_seed):
    """
    GIVEN a test client and a non-existent annotation class ID
    WHEN the client tries to delete the annotation class using a DELETE request
    THEN the response should have a status code of 404
    """

    # Arrange
    params = {'annotation_class_id': 9999}  # Non-existent ID

    # Act
    response = test_client.delete('/api/v1/class/', query_string=params)

    # Assert
    assert response.status_code == 404
    data = response.get_json()

def test_delete_mask_annotation_class(test_client, db_session, annotations_seed):
    """
    GIVEN a test client and the mask annotation class ID
    WHEN the client tries to delete the mask annotation class using a DELETE request
    THEN the response should have a status code of 400 and the appropriate error message
    """

    # Arrange
    mask_class_id = 1  # Assuming 1 is the MASK_CLASS_ID
    params = {'annotation_class_id': mask_class_id}

    # Act
    response = test_client.delete('/api/v1/class/', query_string=params)

    # Assert
    assert response.status_code == 400
    data = response.get_json()



def test_search_annotation_class(test_client, db_session):
    """
    GIVEN a test client and multiple annotation classes
    WHEN the client searches for annotation classes using a GET request
    THEN the response should have a status code of 200 and the returned data should match the search criteria
    """

    # Arrange
    annotation_class1 = AnnotationClass(project_id=1, name="Searchable Class 1", color="#111111", work_mag=10, work_tilesize=2048)
    annotation_class2 = AnnotationClass(project_id=1, name="Searchable Class 2", color="#222222", work_mag=15, work_tilesize=2048)
    db_session.add_all([annotation_class1, annotation_class2])
    db_session.commit()

    params = {'name': "Searchable Class 1"}

    # Act
    response = test_client.get('/api/v1/class/search', query_string=params)

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['id'] == annotation_class1.id
    assert data[0]['name'] == annotation_class1.name
    assert data[0]['color'] == annotation_class1.color
    assert data[0]['work_mag'] == annotation_class1.work_mag