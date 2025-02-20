export const TOOLBAR_KEYS = Object.freeze({
    POINTER: '0',
    IMPORT: '1',
    BRUSH: '2',
    WAND: '3',
    ERASER: '4',
    POLYGON: '5',
})

export const LAYER_KEYS = Object.freeze({
    GT: 0,
    PRED: 1,
    OSM: 2,
    ANN: 3
})

export enum TILE_STATUS {
    UNSEEN = 0,
    STARTPROCESSING,
    PROCESSING,
    DONEPROCESSING
}