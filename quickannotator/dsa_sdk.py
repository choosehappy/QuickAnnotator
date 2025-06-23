import requests
import urllib.parse
import json

class DSAClient:
    # NOTE: may alternatively want to accept a token.
    def __init__(self, base_url, api_key, duration=1):
        """
        Initialize the DSA SDK.

        Args:
            base_url (str): The base URL of the DSA server.
            api_key (str, optional): The API key to generate the Girder authentication token.
            duration (int, optional): The duration (in days) for which the token is valid.
        """
        self.base_url = base_url.rstrip('/')
        self.token = None
        try:
            self.token = self.get_token_with_api_key(api_key, duration)
        except Exception as e:
            raise Exception(f"Failed to get token: {e}")

    def set_token(self, token):
        """
        Set the Girder authentication token.

        Args:
            token (str): The Girder authentication token.
        """
        self.token = token

    def get_token_with_api_key(self, api_key, duration=1):
        """
        Retrieve a temporary token using an API key.

        Args:
            api_key (str): The API key to use for generating the token.
            duration (int): The duration (in days) for which the token is valid.

        Returns:
            str: The temporary token.
        """
        url = f"{self.base_url}/api/v1/api_key/token"
        params = {"key": api_key, "duration": duration}
        headers = {'accept': 'application/json'}
        response = requests.post(url, headers=headers, params=params)
        if response.status_code == 200:
            try:
                token = response.json()['authToken']['token']
                return token
            except (KeyError, ValueError) as e:
                raise Exception(f"Malformed response: {response.text}")
        else:
            raise Exception(f"Failed to retrieve token: {response.status_code} {response.text}")

    def post_file(self, parent_id, file_id, name, user_id, payload_size) -> str:
        """
        Post a file to the DSA server.

        Args:
            parent_id (str): The parent ID for the request.
            file_id (str): The file ID for the request.
            name (str): The name of the file.
            user_id (str): The user ID for the request.
            payload_size (int): The size of the payload.

        Returns:
            Response: The response object from the HTTP request.
        """
        reference = {
            "identifier": "LargeImageAnnotationUpload",
            "itemId": parent_id,
            "fileId": file_id,
            "userId": user_id
        }
        params = {
            "parentType": "item",
            "parentId": parent_id,
            "name": name,
            "size": payload_size,
            "reference": json.dumps(reference),
        }
        url = f"{self.base_url}/api/v1/file"
        headers = {
            'Girder-Token': self.token,
            'Content-Type': 'text/plain'
        }
        response = requests.post(url, headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to post file: {response.status_code} {response.text}")
        else:
            return response.json().get('_id')

    def post_file_chunk(self, chunk, upload_id, offset):
        """
        Post a file chunk to the DSA server.

        Args:
            chunk (str): The chunk of data to send.
            upload_id (str): The upload ID for the file.
            offset (int): The offset of the chunk.

        Returns:
            Response: The response object from the HTTP request.
        """
        params = {"uploadId": upload_id, "offset": offset}
        url = f"{self.base_url}/api/v1/file/chunk"
        headers = {
            'Girder-Token': self.token,
            'Content-Type': 'text/plain'
        }
        response = requests.post(url, headers=headers, params=params, data=chunk)
        return response
    
    def get_user_by_token(self):
        """
        Get the user information using the authentication token.

        Returns:
            dict: The user information.
        """
        url = f"{self.base_url}/api/v1/user/me"
        headers = {'Girder-Token': self.token}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get user by token: {response.status_code} {response.text}")
        

    def get_item_by_name(self, folder_id, name):
        """
        Get the first item by its name in a specific folder.

        Args:
            folder_id (str): The ID of the folder.
            name (str): The name of the item.

        Returns:
            dict: The first item information, if found.
        """
        url = f"{self.base_url}/api/v1/item"
        headers = {'Girder-Token': self.token}
        params = {'folderId': folder_id, 'name': name}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            items = response.json()
            if items:
                return items[0]  # Return the first item
            else:
                raise Exception("No items found with the specified name.")
        else:
            raise Exception(f"Failed to get item by name: {response.status_code} {response.text}")