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