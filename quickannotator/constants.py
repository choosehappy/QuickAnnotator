import enum

class TileStatus(enum.IntEnum):
    UNSEEN = 0
    STARTPROCESSING = 1
    PROCESSING = 2
    DONEPROCESSING = 3

class PolygonOperations(enum.IntEnum):
    UNION = 0
    DIFFERENCE = 1

class ImageType(enum.IntEnum):
    IMAGE = 0
    THUMBNAIL = 1

MASK_DILATION = 1
BASE_PATH = '/opt/QuickAnnotator/quickannotator'

MASK_CLASS_ID = 1

TILE_PRED_EXPIRE = 1 # minutes

MAX_ACTORS_PROCESSING = 1

FLASK_DATETIME_FORMAT = 'iso'

BATCH_SIZE= 1000