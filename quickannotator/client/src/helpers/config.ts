import { ModalData, ProjectModalData, PopoverData } from "../types";

export enum TOOLBAR_KEYS {
    POINTER = '0',  // TODO: should use int enum here.
    IMPORT = '1',
    BRUSH = '2',
    WAND = '3',
    POLYGON = '4',
}

export enum INTERACTION_MODE {
    POINTER = 0,
    POINT_IMPORT,
    LASSO_IMPORT,
    BRUSH,
    WAND,
    ERASER,
    POLYGON,
}

export enum LAYER_KEYS {
    GT = 0,
    PRED,
    OSM,
    ANN,
    BRUSH,
}

export enum TILE_STATUS {
    UNSEEN = 0,
    STARTPROCESSING,
    PROCESSING,
    DONEPROCESSING
}

export enum POLYGON_OPERATIONS {
    UNION = 0,
    DIFFERENCE,
}

export const DEFAULT_CLASS_ID = 1;
export const RENDER_PREDICTIONS_INTERVAL = 8000; // ms  TODO: app setting
export const RENDER_DELAY = 100; // ms  TODO: app setting
export const MAP_TRANSLATION_DELAY = 500; // ms TODO: app setting

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
    DELETE_CLASS: {
        id: 2,
        title: 'Delete annotation class',
        description: 'Are you sure you want to delete this annotation class? This action will remove all annotations of this class and will permenantly delete the deep learning model.',
    },
    EXPORT_CONF: {
        id: 3,
        title: 'Export Annotations',
        description: 'How would you like to export the annotations from this image?',
    },
}


export const POPOVER_DATA: { [key: string]: PopoverData } = {
    FULLSCREEN_TOOL: {
        title: 'Fullscreen Tool',
        description: 'Toggle fullscreen mode for the application window.',
    },
    UNDO_TOOL: {
        title: 'Undo Tool',
        description: 'Revert the last action performed on the current annotation.',
    },
    REDO_TOOL: {
        title: 'Redo Tool',
        description: 'Reapply the last action that was undone on the current annotation.',
    },
    PAN_TOOL: {
        title: 'Pan Tool',
        description: 'Pan around the image. You can temporarily enable this tool by holding down the middle mouse button.',
    },
    IMPORT_TOOL: {
        title: 'Import Tool',
        description: 'Select predicted annotation to save them as ground truth annotations. Click to select a single prediction, or hold CTRL to lasso multiple predictions.',
    },
    BRUSH_TOOL: {
        title: 'Brush Tool',
        description: 'Brush tool for annotation. Hold CTRL to switch to eraser mode.',
    },
    MAGIC_TOOL: {
        title: 'Magic Tool',
        description: 'Magic tool for annotation.',
    },
    POLYGON_TOOL: {
        title: 'Polygon Tool',
        description: 'Polygon tool for annotation. Hold CTRL to switch to eraser mode.',
    },
}

// Viewport settings
export const UI_SETTINGS = {
    gtOpacity: 0.5,
    gtStrokeColor: 'white',
    gtCurrentAnnotationStrokeColor: 'black',
    gtStrokeWidth: 2,
    predOpacity: 0.5,
    highlightedPredColor: 'red',
    pendingTileFillColor: 'grey',
    pendingTileFillOpacity: 0.5,
}

// Hotkeys
export const PAN_TOOL_HOTKEY = '1';
export const IMPORT_TOOL_HOTKEY = '2';
export const BRUSH_TOOL_HOTKEY = '3';
export const WAND_TOOL_HOTKEY = '4';
export const POLYGON_TOOL_HOTKEY = '5';

const ADD_POLYGON_COLOR = { r: 0, g: 0, b: 1 };
const SUBTRACT_POLYGON_COLOR = { r: 1, g: 0, b: 0 };
export const BRUSH_SIZE = 20;


export const POLYGON_CREATE_STYLE = {
    closed: true,
    stroke: true,
    strokeColor: ADD_POLYGON_COLOR,
    strokeWidth: 3,
};


export const POLYGON_CREATE_STYLE_SECONDARY = {
    closed: true,
    stroke: true,
    strokeColor: SUBTRACT_POLYGON_COLOR,
    strokeWidth: 3,
};


export const IMPORT_CREATE_STYLE = {
    closed: true,
    fill: true, // BUG: Fill does not work for some reason.
    fillColor: { r: 1, g: 0.5, b: 0 },
    stroke: true,
    strokeColor: { r: 1, g: 0.5, b: 0 },
    strokeWidth: 3,
    fillOpacity: 0.9,
};


export const BRUSH_CREATE_STYLE = {  
    radius: BRUSH_SIZE,  
    scaled: false, // This prevents scaling with zoom  
    fill: true,  
    fillColor: {r: 0, g: 1, b: 0},  
    stroke: true,  
    strokeColor: ADD_POLYGON_COLOR  
};


export const BRUSH_CREATE_STYLE_SECONDARY = {  
    radius: BRUSH_SIZE,  
    scaled: false, // This prevents scaling with zoom  
    fill: true,  
    fillColor: {r: 0, g: 1, b: 0},  
    stroke: true,  
    strokeColor: SUBTRACT_POLYGON_COLOR  
};


export const MASK_CLASS_ID = 1; // TODO: app setting

export const SERVER_URL = 'http://localhost:5000'; // TODO: app setting
export const API_URI = '/api/v1';   // TODO: app setting
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
    },
    REMOVE: {
        id: 2,
        title: 'Delete Project',
        text: 'Are you sure you want to delete this project?',
        btnText:'Delete'
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

// Cookie names
export enum COOKIE_NAMES {
    SKIP_CONFIRM_IMPORT = 'skipConfirmImport',
    SKIP_CONFIRM_DELETE_CLASS = 'skipConfirmDeleteClass',
}