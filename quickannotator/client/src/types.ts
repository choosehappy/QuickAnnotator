import {MultiPolygon, Point, Polygon, Feature} from "geojson"

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

export interface Annotation {
    id: number;
    polygon: MultiPolygon;
    centroid: Point;
    area: number;
    custom_metrics: { [key: string]: unknown }
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
    image_id: number;
    annotation_class_id: number;
    geom: {};
    seen: number;
}

export type OutletContextType = {
    currentProject: Project;
    setCurrentProject: (project: Project | null) => void;
    currentImage: Image;
    setCurrentImage: (image: Image | null) => void;
}