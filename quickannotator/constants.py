import enum

class TileStatus(enum.IntEnum):
    UNSEEN = 0
    STARTPROCESSING = 1
    PROCESSING = 2
    DONEPROCESSING = 3

MASK_DILATION = 1