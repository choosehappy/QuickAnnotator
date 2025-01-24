import {Point, Polygon, Feature} from "geojson"

export interface AnnotationClass {
    id: number;
    project_id: number;
    name: string;
    color: string;
    magnification: number;
    patchsize: number;
    tilesize: number;
    date: Date;
    dl_model_objectref: string;
}

export interface AnnotationResponse {
    id: number;
    annotation_class_id: number;
    tile_id: number;
    polygon: Polygon;
    centroid: Point;
    area: number;
    custom_metrics: { [key: string]: unknown }
}

export class Annotation {
    id: number;
    tileId: number | null;
    annotation_class_id: number;
    polygon: string;
    centroid: string;
    area: number;
    custom_metrics: { [key: string]: unknown }

    constructor(annotation: AnnotationResponse, tileId: number | null = null) {
        this.id = annotation.id;
        this.tileId = tileId;
        this.annotation_class_id = annotation.annotation_class_id;
        this.polygon = annotation.polygon;
        this.centroid = annotation.centroid;
        this.area = annotation.area;
        this.custom_metrics = annotation.custom_metrics;
    }

    setTileId(tileId: number | null) {
        this.tileId = tileId;
    }

    get parsedPolygon(): Polygon {
        return JSON.parse(this.polygon);
    }

    get parsedCentroid(): Point {
        return JSON.parse(this.centroid);
    }
}

export interface PostAnnArgs {
    is_gt: boolean;
    polygon: string;
}

export interface PostOperationArgs extends AnnotationResponse {
    polygon2: string;
    operation: number;
}

export interface PutAnnArgs extends AnnotationResponse {
    is_gt: boolean;
}

export interface Image {
    id: number;
    project_id: number;
    name: string;
    path: string;
    height: number;
    width: number;
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

export interface Tile {
    id: number;
    annotation_class_id: number;
    image_id: number;
    tile_id: number;
    seen: number;
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