import enum

class TileStatus(enum.IntEnum):
    UNSEEN = 0
    STARTPROCESSING = 1
    PROCESSING = 2
    DONEPROCESSING = 3

class AnnsFormatEnum(enum.IntEnum):
    GEOJSON = 0
    GEOJSON_NO_PROPS = 1

class PropsFormatEnum(enum.IntEnum):
    TSV = 0

MASK_DILATION = 1
BASE_PATH = '/opt/QuickAnnotator/quickannotator'

MASK_CLASS_ID = 1

TILE_PRED_EXPIRE = 1 # minutes

MAX_ACTORS_PROCESSING = 1

FLASK_DATETIME_FORMAT = 'iso'

STREAMING_CHUNK_SIZE = 8192 # in bytes

POST_FILE_CHUNK_SIZE = 1024 * 1024 * 16 # 16MB