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

# TODO: move to project settings
MAGNIFICATION_OPTIONS = [1.25, 2.5, 5.0, 10.0, 20.0, 40.0]  

TILESIZE_OPTIONS = [256, 512, 1024, 2048] # in pixels