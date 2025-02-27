import enum

class TileStatus(enum.IntEnum):
    UNSEEN = 0
    STARTPROCESSING = 1
    PROCESSING = 2
    DONEPROCESSING = 3

BASE_PATH = '/opt/QuickAnnotator/quickannotator'

MASK_CLASS_ID = 1