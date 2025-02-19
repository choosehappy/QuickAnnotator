import enum

class TileStatus(enum.IntEnum):
    UNSEEN = 0
    PROCESSING = 1
    SEEN = 2