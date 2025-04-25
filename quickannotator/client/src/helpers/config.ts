import { ModalData } from "../types";

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

export const DEFAULT_CLASS_ID = 1;

export const RENDER_PREDICTIONS_INTERVAL = 8000; // ms
export const RENDER_DELAY = 100; // ms
export const MAP_TRANSLATION_DELAY = 500; // ms

export const MODAL_DATA: { [key: string]: ModalData } = {
    IMPORT_CONF: {
        id: 0,
        title: 'Import annotations',
        description: 'Are you sure you want to import annotations?',
    },
    ADD_CLASS: {
        id: 1,
        title: 'Add a new annotation class',
        description: 'Configure the new annotation class',
    },
}


export const POPOVER_DATA = {

}