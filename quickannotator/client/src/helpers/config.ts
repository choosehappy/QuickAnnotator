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

export const RENDER_PREDICTIONS_INTERVAL = 8000; // ms
export const RENDER_DELAY = 100; // ms
export const MAP_TRANSLATION_DELAY = 500; // ms

export const MODAL_DATA: { [key: string]: ModalData } = {
    IMPORT_CONF: {
        id: 0,
        title: 'Import Annotations',
        description: 'Are you sure you want to import annotations?',
    },
    EXPORT_CONF: {
        id: 1,
        title: 'Export Annotations',
        description: 'How would you like to export the annotations from this image?',
    },
}


export const POPOVER_DATA = {

}

export const TISSUE_MASK_CLASS_ID = 1;