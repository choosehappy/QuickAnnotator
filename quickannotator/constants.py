import enum
import os


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
    
class PolygonOperations(enum.IntEnum):
    UNION = 0
    DIFFERENCE = 1

class ImageType(enum.IntEnum):
    IMAGE = 0
    THUMBNAIL = 1

class NamedRayActorType(enum.Enum):
    ANNOTATION_EXPORTER = 'exporter'
    
class ExportFormatExtensions(enum.Enum):
    GEOJSON = 'geojson'
    TSV = 'tsv'


MASK_DILATION = 1
BASE_PATH = '/opt/QuickAnnotator'
MOUNTS_PATH = os.path.join(BASE_PATH, 'quickannotator/mounts')

MASK_CLASS_ID = 1

TILE_PRED_EXPIRE = 1 # minutes

MAX_ACTORS_PROCESSING = 1   # TODO: app setting

FLASK_DATETIME_FORMAT = 'iso'

STREAMING_CHUNK_SIZE = 8192 # in bytes  # TODO: app setting

POST_FILE_CHUNK_SIZE = 1024 * 1024 * 16 # 16MB  # TODO: app setting