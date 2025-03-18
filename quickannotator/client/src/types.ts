import {Point, Polygon, Feature} from "geojson"
import { TILE_STATUS } from "./helpers/config";

export interface AnnotationClass {
    id: number;
    project_id: number;
    name: string;
    color: string;
    work_mag: number;
    work_tilesize: number;
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
    id: number;
    name: string;
    description: string;
    date: Date;
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
    seen: TILE_STATUS;
    hasgt: boolean;
    date: Date;
}

export type OutletContextType = {
    currentProject: Project;
    setCurrentProject: (project: Project | null) => void;
    currentImage: Image;
    setCurrentImage: (image: Image | null) => void;
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

    addAnnotation(annotation: Annotation) {
        this.undoStack.push(annotation);
        this.redoStack = [];
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

export interface ModalData {
    id: number;
    title: string;
    description: string;
}