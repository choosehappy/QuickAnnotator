import { ModalData, ProjectModalData } from "../types";

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
    }
}


export const POPOVER_DATA = {

}

export enum PROJECT_MODAL_STATUS {
    // 0 - create, 1 - update, 2 - remove
    CREATE = 0,
    UPDATE,
    REMOVE
}
// upload accepted files format
export const PROJECT_EDIT_MODAL_DATA: { [key: string]: ProjectModalData } = {
    ADD: {
        id: 0,
        title: 'New Project',
        text: 'Create a New Project Below',
        btnText:'Add'
    },
    EDIT: {
        id: 1,
        title: 'Edit Project',
        text: 'Update The Project Below',
        btnText:'Update'
    }
}

export const PROJECT_CONFIG_OPTIONS = [
    {'text':'< 1000 Whole Slide Images','value':'false'},
    {'text':'> 1000 Whole Slide Images','value':'true'}
]


export const UPLOAD_ACCEPTED_FILES = {
    'application/x-svs': ['.svs', '.ndpi'],
    'application/dicom': ['.dcm'],
    'application/json': ['.json', '.geojson'],
}

// WSI file extension
export const WSI_EXTS = ['svs', 'tif','dcm','vms', 'vmu', 'ndpi',
    'scn', 'mrxs','tiff','svslide','bif','czi']

// JSON file extension
export const JSON_EXTS = ['json','geojosn']