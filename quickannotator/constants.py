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
        "#D5FF00", "#00FF00", "#FF937E", "#91D0CB", 
        "#0000FF", "#00AE7E", "#FF00F6", "#5FAD4E", 
        "#01D0FF", "#BB8800", "#BDC6FF", "#008F9C", 
        "#A5FFD2", "#FFA6FE", "#FFDB66", "#00FFC6", 
        "#00B917", "#BDD393", "#004754", "#010067", 
        "#0E4CA1", "#005F39", "#6B6882", "#683D3B", 
        "#43002C", "#788231"
    ]
}

# TODO: move to project settings
MAGNIFICATION_OPTIONS = [1.25, 2.5, 5.0, 10.0, 20.0, 40.0]  

TILESIZE_OPTIONS = [256, 512, 1024, 2048] # in pixels