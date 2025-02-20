from pymemcache.client.base import PooledClient
from pymemcache import serde
import os, io 
from PIL import Image as PILImage
import numpy as np

def compress_to_jpeg(matrix):
    # Convert NumPy matrix to a PIL Image
    image = PILImage.fromarray(matrix.astype(np.uint8))
    # Save the image to a BytesIO object as JPEG
    with io.BytesIO() as output:
        image.save(output, format="JPEG")
        jpeg_bytes = output.getvalue()  # Get the byte data
    return jpeg_bytes

# Function to decompress JPEG bytes back to a NumPy array
def decompress_from_jpeg(jpeg_bytes):
    # Open the byte data as an image using PIL
    with io.BytesIO(jpeg_bytes) as input:
        image = PILImage.open(input)
        # Convert image back to NumPy array
        matrix = np.array(image)
    return matrix


#-----
def get_memcached_client():
    client = PooledClient(('localhost', 11211),serde=serde.pickle_serde, max_pool_size=4) #TODO: will need to get this info from the config file
    return client