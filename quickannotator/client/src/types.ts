import {Point, Polygon, Feature} from "geojson"
import { TILE_STATUS } from "./helpers/config";

export interface IdNameElement {
    id: number;
    name: string;
}

export interface Project extends IdNameElement{
    description: string;
    date: Date;
}

export interface AnnotationClass extends IdNameElement {
    project_id: number;
    color: string;
    work_mag: number;
    work_tilesize: number;
    datetime: Date;
}

export interface Image extends IdNameElement{
    project_id: number;
    path: string;
    base_height: number;
    base_width: number;
    dz_tilesize: number;
    embeddingCoord: string;
    group_id: number;
    split: number;
    date: Date;
}

export interface AnnotationResponse {
    id: number;
    tile_id: number;
    polygon: string;
    centroid: string;
    area: number;
    custom_metrics: { [key: string]: unknown }
    datetime: Date;
}

export class Annotation {
    id: number;
    annotation_class_id: number;
    tile_id: number | null;
    polygon: string;
    centroid: string;
    area: number;
    custom_metrics: { [key: string]: unknown }
    datetime: Date;

    constructor(annotation: AnnotationResponse, annotation_class_id: number) {
        this.id = annotation.id;
        this.tile_id = annotation.tile_id;
        this.annotation_class_id = annotation_class_id;
        this.polygon = annotation.polygon;
        this.centroid = annotation.centroid;
        this.area = annotation.area;
        this.custom_metrics = annotation.custom_metrics;
        this.datetime = annotation.datetime;
    }

    setTileId(tile_id: number | null) {
        this.tile_id = tile_id;
    }

    get parsedPolygon(): Polygon {
        return JSON.parse(this.polygon);
    }

    get parsedCentroid(): Point {
        return JSON.parse(this.centroid);
    }
}

export interface PostAnnsArgs {
    polygons: string[];
}

export interface QueryAnnsByPolygonArgs {
    polygon: string;
    is_gt: boolean;
}

export interface SearchTileIdsByPolygonArgs {
    polygon: string;
    hasgt: boolean;
}

export interface PostOperationArgs extends AnnotationResponse {
    polygon2: string;
    operation: number;
}

export interface PutAnnArgs {
    polygon: string;
    annotation_id: number;
    is_gt: boolean;
}

export interface PostAnnClassArgs {
    name: string;
    color: string;
    work_mag: number;
    project_id: number;
}

export interface Image {
    id: number;
    project_id: number;
    name: string;
    path: string;
    base_height: number;
    base_width: number;
    dz_tilesize: number;
    embeddingCoord: string;
    group_id: number;
    split: number;
    date: Date;
}

export interface Project {
    id: number | null;
    name: string;
    is_dataset_large: boolean;
    description: string;
    datetime: Date;
}

export interface TileIds {
    tile_ids: number[];
    is_gt: boolean;
}

export interface Tile {
    id: number;
    annotation_class_id: number;
    image_id: number;
    tile_id: number;
    pred_status: TILE_STATUS;
    pred_datetime: Date | null;
    gt_counter: number | null;
    gt_datetime: Date | null;
}

export type OutletContextType = {
    currentProject: Project;
    setCurrentProject: (project: Project | null) => void;
    currentImage: Image;
    setCurrentImage: (image: Image | null) => void;
}

export type ToolbarButton = {
        icon: JSX.Element;
        disabled: boolean;
        title: string;
        shortcut: string;
        content: PopoverData;
};

export enum ExportFormat {
    GEOJSON = "geojson",
    TSV = "tsv"
}

export enum UploadStatus {
    selected = 0,
    uploading = 1,
    pending = 2,
    error = 3,
    done = 4,
}

export type UploadFileStore = {
    [fileName: string]: {
        progress: number;
        status: UploadStatus;
    };
}

export type DropzoneFile = {
    file: File;
    status: UploadStatus;
}

export class CurrentAnnotation {
    undoStack: Annotation[];
    redoStack: Annotation[];

    constructor(annotation: Annotation) {
        this.undoStack = [annotation];
        this.redoStack = [];
    }

    get currentState() {
        return this.undoStack.at(-1);
    }

    // Note that useState objects cannot be mutated directly, so we have to return a new object.
    addAnnotation(annotation: Annotation): CurrentAnnotation {
        const newCurrentAnnotation = new CurrentAnnotation(this.undoStack[0]);
        newCurrentAnnotation.undoStack = [...this.undoStack, annotation];
        newCurrentAnnotation.redoStack = [];
        return newCurrentAnnotation;
    }

    undo() {
        if (this.undoStack.length > 1) {
            const annotation = this.undoStack.pop();
            if (annotation) {
                this.redoStack.push(annotation);
            }
        }
    }

    redo() {
        if (this.redoStack.length > 0) {
            const annotation = this.redoStack.pop();
            if (annotation) {
                this.undoStack.push(annotation);
            }
        }
    }
}
export interface ProjectModalData {
    id: number;
    title: string;
    text: string;
    btnText: string;
}
export interface ModalData {
    id: number;
    title: string;
    description: string;
}

export interface PopoverData {
    title: string;
    description: string;
}

export class DataItem {
    id: number;
    name: string;
    selected: boolean;

    constructor(elem: IdNameElement) {
        this.id = elem.id;
        this.name = elem.name;
        this.selected = true;
    }

    toggleSelected() {
        this.selected = !this.selected;
    }
}
