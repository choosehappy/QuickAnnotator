import {MultiPolygon, Point} from "geojson"

export default interface Annotation {
    id: number;
    polygon: MultiPolygon;
    centroid: Point;
    area: number;
    customMetrics: { [key: string]: unknown }
}

