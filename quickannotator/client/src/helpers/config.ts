export enum TOOLBAR_KEYS {
    POINTER = '0',
    IMPORT = '1',
    BRUSH = '2',
    WAND = '3',
    ERASER = '4',
    POLYGON = '5',
}

export enum LAYER_KEYS {
    GT = 0,
    PRED,
    OSM,
    ANN,
}

export enum TILE_STATUS {
    UNSEEN = 0,
    STARTPROCESSING,
    PROCESSING,
    DONEPROCESSING
}