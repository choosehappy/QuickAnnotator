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
