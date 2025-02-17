import enum

class TileStatus(enum.Enum):
    UNSEEN = 0
    PROCESSING = 1
    SEEN = 2