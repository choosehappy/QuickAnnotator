import enum

class TileStatus(enum.IntEnum):
    UNSEEN = 0
    STARTPROCESSING = 1
    PROCESSING = 2
    DONEPROCESSING = 3

MASK_DILATION = 1
BASE_PATH = '/opt/QuickAnnotator/quickannotator'

MASK_CLASS_ID = 1

TILE_PRED_EXPIRE = 1 # minutes

MAX_ACTORS_PROCESSING = 1

FLASK_DATETIME_FORMAT = 'iso'

COLOR_PALETTES = {
    'default': {
        '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
        '#800000', '#008000', '#000080', '#808000', '#800080', '#008080',
        '#C0C0C0', '#808080', '#999999', '#666666', '#333333',
    }
}

# TODO: move to project settings
MAGNIFICATION_OPTIONS = [1.25, 2.5, 5.0, 10.0, 20.0, 40.0]  