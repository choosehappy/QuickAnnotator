import hashlib

def test_ERD(test_client):
    """
    GIVEN a test client
    WHEN the client requests the ER diagram
    THEN the response should have a status code of 200 and the content type should be 'image/png'
    AND the response data should not be empty
    """
    # Arrange
    target_img_path = 'quickannotator/tests/testdata/ERD.png'

    # Act
    response = test_client.get('/api/v1/misc/erd')

    # Assert
    assert response.status_code == 200
    assert response.content_type == 'image/png'
    # Calculate checksum of the response data
    response_checksum = hashlib.md5(response.data).hexdigest()

    # Read the expected image and calculate its checksum
    with open(target_img_path, 'rb') as f:
        expected_checksum = hashlib.md5(f.read()).hexdigest()

    # Assert that the checksums match
    assert response_checksum == expected_checksum