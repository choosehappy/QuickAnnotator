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