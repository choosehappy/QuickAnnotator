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


TILE_PRED_EXPIRE = 1 # minutes

MAX_ACTORS_PROCESSING = 1   # TODO: app setting

FLASK_DATETIME_FORMAT = 'iso'


COLOR_PALETTE_NAME = 'default'  # TODO: project setting

ANNOTATION_CLASS_COLOR_PALETTES = {
    # https://informatics-isi-edu.github.io/atlas-d2k-docs/docs/color-palette-for-image-annotation/
    'default': [
        "#d5ff00", "#00ff00", "#ff937e", "#91d0cb", 
        "#0000ff", "#00ae7e", "#ff00f6", "#5fad4e", 
        "#01d0ff", "#bb8800", "#bdc6ff", "#008f9c", 
        "#a5ffd2", "#ffa6fe", "#ffdb66", "#00ffc6", 
        "#00b917", "#bdd393", "#004754", "#010067", 
        "#0e4ca1", "#005f39", "#6b6882", "#683d3b", 
        "#43002c", "#788231"
    ]
}

MASK_CLASS_ID = 1
MASK_CLASS_NAME = "Tissue Mask"
MASK_CLASS_COLOR_IDX = 0
MASK_CLASS_WORK_MAG = 1.25
MASK_CLASS_WORK_TILESIZE = 2048

# TODO: move to project settings
MAGNIFICATION_OPTIONS = [1.25, 2.5, 5.0, 10.0, 20.0, 40.0]  

TILESIZE_OPTIONS = [256, 512, 1024, 2048] # in pixels
STREAMING_CHUNK_SIZE = 8192 # in bytes  # TODO: app setting

POST_FILE_CHUNK_SIZE = 1024 * 1024 * 16 # 16MB  # TODO: app setting
IMPORT_ANNOTATION_BATCH_SIZE= 1000

class AnnotationFileFormats(enum.Enum):
    JSON = 'json'
    GEOJSON = 'geojson'


class Dialects(enum.Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"

CHECKPOINT_FILENAME = "model.safetensors"

class LoggerNames(enum.Enum):
    FLASK = "flask"
    RAY = "qa_ray"     # NOTE: "ray" conflicts with the ray logger, resulting in ray._private logs getting saved to the db logs table.
    DB = "db"


# Memcached settings
MEMCACHED_HOST = 'localhost'
MEMCACHED_PORT = 11211
MAX_POOL_SIZE = 4


class ImageFormat(enum.Enum):
    PNG = "PNG"
    JPG = "JPEG"


class AnnotationReturnMode(enum.IntEnum):
    GEOJSON = 0
    WKT = 1