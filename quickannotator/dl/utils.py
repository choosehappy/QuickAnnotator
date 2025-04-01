import large_image
from pymemcache.client.base import PooledClient
from pymemcache import serde
import os, io 
from PIL import Image as PILImage
import numpy as np
from quickannotator.db import get_session

from quickannotator.db.models import Image, AnnotationClass
from quickannotator.api.v1.utils.coordinate_space import TileSpace

def compress_to_jpeg(matrix):
    # Convert NumPy matrix to a PIL Image
    image = PILImage.fromarray(matrix.astype(np.uint8))
    # Save the image to a BytesIO object as JPEG
    with io.BytesIO() as output:
        image.save(output, format="PNG") ##TODO: The issue here, if we use JPEG, the mask file loses a lot of resolution. we could likely jack up the quality parameter, and still get excellent compression
                                        #however, we may need to modify this to accept a quality parameter, sicne the image and mask should likely have different values?
                                        #seems like something to do afterward --- setting to PNG to retain perfect quality
                                        #note as well, setting this to JPEG, will yield masks with values >1, due to overlapping polygons
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


def load_tile(tile): #TODO: i suspect this sort of function exists elsewhere within QA to serve tiles to the front end? change to merge functionality?
    with get_session() as db_session:
        image = db_session.query(Image).filter_by(id=tile.image_id).first()
        annoclass = db_session.query(AnnotationClass).filter_by(id=tile.annotation_class_id).first()
        db_session.expunge_all()

    image_path = image.path
    
    li = large_image.getTileSource(os.path.join("/opt/QuickAnnotator/quickannotator", image_path)) #TODO: JANKY


    #---- two options here
    sizeXtargetmag, sizeYtargetmag= li.getPointAtAnotherScale((li.sizeX,li.sizeY), #TODO: should this be modfieid somehow to not use Large image?
                                                                targetScale={'magnification': annoclass.work_mag}, 
                                                                targetUnits='mag_pixels') 
    
    #x,y=tileid_to_point(tile.tile_size,sizeXtargetmag,sizeYtargetmag,tile.tile_id)   #REFACTORED --- if working, delete this comment

    ts = TileSpace(annoclass.work_tilesize, sizeXtargetmag, sizeYtargetmag)
    x,y = ts.tileid_to_point(tile.tile_id) 

    region, _ = li.getRegion(region=dict(left=x, top=y, width=annoclass.work_tilesize, height=annoclass.work_tilesize,units='pixels'), 
                                            scale={'magnification':annoclass.work_mag},format=large_image.tilesource.TILE_FORMAT_NUMPY)

    io_image = region[:,:,:3] #np.array(region.convert("RGB"))


    # Get actual height and width
    actual_height, actual_width, _ = io_image.shape

    # Compute padding amounts
    pad_height = max(0, annoclass.work_tilesize - actual_height)
    pad_width = max(0, annoclass.work_tilesize - actual_width)

    # Apply padding (black is default since mode='constant' and constant_values=0)
    io_image = np.pad(io_image, 
                    ((0, pad_height), (0, pad_width), (0, 0)), 
                    mode='constant', 
                    constant_values=0)
    
    return io_image,x,y


#-----
def get_memcached_client():
    client = PooledClient(('localhost', 11211),serde=serde.pickle_serde, max_pool_size=4) #TODO: will need to get this info from the config file
    return client