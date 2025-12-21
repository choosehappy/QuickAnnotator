import geo from "geojs"
import { Point, Polygon, Feature, Position, GeoJsonGeometryTypes } from "geojson";
import { Annotation, AnnotationClass, FeatureProps, PredFeatureType, TileRef } from "../types";
import { MAX_ZOOM_FOR_DOWNSAMPLE, NUM_LEVELS_FOR_DOWNSAMPLE, UI_SETTINGS } from "../helpers/config";

export const computeFeaturesToRender = (oldFeatureIds: number[], newFeatureIds: number[]) => {
    const a = new Set(oldFeatureIds)
    const b = new Set(newFeatureIds)
    const featuresToRemove = new Set([...a].filter(x => !b.has(x)));
    const featuresToRender = new Set([...b].filter(x => !a.has(x)));
    return { featuresToRemove, featuresToRender }
}

export function getFeatIdsRendered(layer: geo.layer, type: PredFeatureType) {
    return layer.features().filter((f) => f.featureType === 'polygon' && f.props.type === type).map((f) => f.props.featureId);
}

export const getTileFeatureById = (layer: geo.layer, featureId: number, type: PredFeatureType) => {
    return layer.features().find((f: any) => {
        return f.featureType === 'polygon' && f.props.featureId === featureId && f.props.type === type;
    });
};

export const getTileFeatureByTileId = (layer: geo.layer, tileId: number, type: PredFeatureType) => {
    return layer.features().find((f: any) => {
        return f.featureType === 'polygon' && f.props.tileIds?.includes(tileId) && f.props.type === type;
    });
};

export function removeFeatureById(layer: geo.layer, featureId: number, type: PredFeatureType) {
    const feature = getTileFeatureById(layer, featureId, type);
    if (feature) {
        feature.data([]);
        layer.removeFeature(feature);
        feature.draw();
    }
}

export const tileIdIsValid = (tileId: number | null | undefined) => {
    if (tileId === null || tileId === undefined) {
        console.log('Tile ID is invalid:', tileId);
        return false;
    }

    return true;
}

export const redrawTileFeature = (feature: any, options = {}, data?: any[]) => {
    if (!feature) {
        console.warn('Cannot redraw feature, it is undefined.');
        return;
    }
    if (data) {
        feature.data(data);
    }
    console.log(`redrew feature ${feature}`)
    feature.modified();
    feature.draw(options);
}

export class TileRefStore implements Iterable<[number, TileRef[]]> {
    private groups: Map<number, TileRef[]>;

    constructor(tileRefs: TileRef[]) {
        this.groups = new Map();
        this.groupTileRefs(tileRefs);
    }

    private groupTileRefs(tileRefs: TileRef[]) {
        tileRefs.forEach((tileRef) => {
            const downsampledId = tileRef.downsampled_tile_id;
            if (!this.groups.has(downsampledId)) {
                this.groups.set(downsampledId, []);
            }
            this.groups.get(downsampledId)?.push(tileRef);
        });
    }

    getTileRefs(downsampledId: number): TileRef[] | undefined {
        return this.groups.get(downsampledId);
    }

    hasDownsampledId(downsampledId: number): boolean {
        return this.groups.has(downsampledId);
    }

    getAllGroups(): Map<number, TileRef[]> {
        return this.groups;
    }

    getAllGroupIds(): number[] {
        return Array.from(this.groups.keys());
    }

    [Symbol.iterator](): Iterator<[number, TileRef[]]> {
        return this.groups.entries();
    }
}


export const createGTTileFeature = (featureProps: FeatureProps, annotations: Annotation[], layer: any, annotationClass: AnnotationClass, currentAnnotationId: number | null = null) => {
    const feature = layer.createFeature('polygon');
    const color = annotationClass.color;
    feature.props = featureProps;
    feature.props.type = 'annotation';

    feature
        .position((d: Position) => ({ x: d[0], y: d[1] }))
        .polygon((a: Annotation) => ({
            outer: a.parsedPolygon.coordinates[0],
            inner: a.parsedPolygon.coordinates.slice(1)
        }))
        .data(annotations)
        .style('fill', true)
        .style('fillColor', color)
        .style('fillOpacity', UI_SETTINGS.gtOpacity)
        .style('strokeColor', UI_SETTINGS.gtCurrentAnnotationStrokeColor)
        .style('strokeWidth', UI_SETTINGS.gtStrokeWidth)
        .style('stroke', true)
        .style('uniformPolygon', true)

    const originalDraw = feature.draw;
    // Override the draw method to accept options.
    feature.draw = (options = { currentAnnotationId: null }) => {
        if (options.currentAnnotationId) {
            feature.style('strokeColor', (point: number[], pointIdx: number, ann: Annotation, annIdx: number) => {
                return ann.id === options.currentAnnotationId ? 'black' : 'white';
            });
        } else {
            feature.style('strokeColor', 'white');
        }
        originalDraw.call(feature);
    }
    console.log('Drew ground truth polygons.')
    feature.draw({ currentAnnotationId: currentAnnotationId });
    return feature;
}


export const createPredTileFeature = (featureProps: any, annotations: Annotation[], layer: any, annotationClass: AnnotationClass, highlightedPolyIds: number[] | null = null) => {
    const feature = layer.createFeature('polygon');
    const color = annotationClass.color;
    featureProps.type = 'annotation';
    feature.props = featureProps;
    feature
        .position((d: Position) => ({ x: d[0], y: d[1] }))
        .polygon((a: Annotation) => ({
            outer: a.parsedPolygon.coordinates[0],
            inner: a.parsedPolygon.coordinates.slice(1)
        }))
        .data(annotations)
        .style('fill', true)
        .style('fillColor', color)
        .style('fillOpacity', UI_SETTINGS.predOpacity)
        .style('strokeColor', UI_SETTINGS.highlightedPredColor)
        .style('uniformPolygon', true)

    const originalDraw = feature.draw;
    // Override the draw method to accept options.
    feature.draw = (options: { highlightedPolyIds: number[] | null } = { highlightedPolyIds: null }) => {
        const ids = options.highlightedPolyIds;
        if (ids && ids.length > 0) {
            feature.style('stroke', (ann: Annotation) => {
                return ids.includes(ann.id);
            });
        } else {
            feature.style('stroke', false);
        }
        originalDraw.call(feature);
    }
    // console.log('Drew predicted polygons.')
    feature.draw({ highlightedPolyIds: highlightedPolyIds });
    return feature;
}

export const createPendingTileFeature = (featureProps: any, polygons: Polygon[], layer: any) => {
    const feature = layer.createFeature('polygon');
    featureProps.type = 'pending';
    feature.props = featureProps;
    feature
        .position((d: Position) => ({ x: d[0], y: d[1] }))
        .polygon((p: Polygon) => p.coordinates[0])
        .data(polygons)
        .style('fill', true)
        .style('fillColor', UI_SETTINGS.pendingTileFillColor)
        .style('fillOpacity', UI_SETTINGS.pendingTileFillOpacity)
        .style('uniformPolygon', true)
    console.log('Drew pending polygon.')
    feature.draw();
    return feature;
}

export function getScaledSize(geojs_map: geo.map, size: number): number {
    const currentZoom = geojs_map.zoom();
    const scaleFactor = Math.pow(2, currentZoom);
    return size / scaleFactor * geojs_map.unitsPerPixel();  // Scale the size based on the current zoom level
}

export function getTileDownsampleLevel(geojs_map: geo.map): number {
    const currentZoom = geojs_map.zoom();
    console.log(`currentZoom: ${currentZoom}`);
    const zoomThresholds = getZoomThresholds(geojs_map.zoomRange().min, MAX_ZOOM_FOR_DOWNSAMPLE);
    console.log(`zoomThresholds: ${zoomThresholds}`);

    // For descending thresholds:
    // - If currentZoom > threshold[0], return 0
    // - If between threshold[i] and threshold[i+1], return i
    // - If <= last threshold, return zoomThresholds.length - 1
    const idx = zoomThresholds.findIndex((th) => currentZoom > th);
    return idx === -1 ? zoomThresholds.length - 1 : idx;
}

export function getPolygonSimplifyTolerance(geojs_map: geo.map): number {
    return getTileDownsampleLevel(geojs_map) * 10;
}

export function getZoomThresholds(minZoom: number, maxZoom: number): number[] {
    const thresholds: number[] = [];
    const step = (maxZoom - minZoom) / NUM_LEVELS_FOR_DOWNSAMPLE;

    for (let i = 0; i < NUM_LEVELS_FOR_DOWNSAMPLE; i++) {
        thresholds.push(maxZoom - step * i);
    }

    return thresholds;
}



// TODO: define function to get the polygon downsample value based on zoom level


export function createCirclePolygon(x: number, y: number, size: number, layer: geo.layer, pixelTolerance: number): geo.annotation.circleAnnotation {
    const circle = geo.annotation.circleAnnotation({
        layer: layer,
        corners: [
            { x: x - size, y: y - size },  // top-left
            { x: x + size, y: y - size },  // top-right
            { x: x + size, y: y + size },  // bottom-right
            { x: x - size, y: y + size }   // bottom-left
        ],
    });

    return circle.toPolygonList({ pixelTolerance: pixelTolerance }); // Convert to polygon with a pixel tolerance
}

export function createConnectingRectangle(x1: number, y1: number, x2: number, y2: number, size: number) {
    const ang = Math.atan2(y2 - y1, x2 - x1) + Math.PI / 2;
    return [[
        [x1 + size * Math.cos(ang), y1 + size * Math.sin(ang)],
        [x1 - size * Math.cos(ang), y1 - size * Math.sin(ang)],
        [x2 - size * Math.cos(ang), y2 - size * Math.sin(ang)],
        [x2 + size * Math.cos(ang), y2 + size * Math.sin(ang)]
    ]];
};

