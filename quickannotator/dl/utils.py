import os
import shutil
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import Geometry
import shapely.wkb
import numpy as np
import cv2
import numpy as np
from PIL import Image as PILImage
import scipy.ndimage
import io

def get_database_path():
    return '/opt/QuickAnnotator/quickannotator/instance/quickannotator.db'

def load_spatialite(dbapi_connection, connection_record):
    dbapi_connection.enable_load_extension(True)
    dbapi_connection.execute('SELECT load_extension("mod_spatialite")')
    dbapi_connection.execute('SELECT InitSpatialMetaData(1);')

    # Function to convert NumPy array (image) to JPEG bytes
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
from pymemcache.client.base import PooledClient
from pymemcache import serde
def get_memcached_client():
    client = PooledClient(('localhost', 11211),serde=serde.pickle_serde, max_pool_size=4)
    return client