import geo from "geojs"
import { Point, Polygon, Feature, Position, GeoJsonGeometryTypes } from "geojson";
import { Annotation, AnnotationClass } from "../types";
import { UI_SETTINGS } from "../helpers/config";

export const computeTilesToRender = (oldTileIds: number[], newTileIds: number[]) => {
    const a = new Set(oldTileIds)
    const b = new Set(newTileIds)
    const tilesToRemove = new Set([...a].filter(x => !b.has(x)));
    const tilesToRender = new Set([...b].filter(x => !a.has(x)));
    return { tilesToRemove, tilesToRender }
}

export function getFeatIdsRendered(layer: geo.layer, type: string) {
    return layer.features().filter((f) => f.featureType === 'polygon' && f.props.type === type).map((f) => f.props.tile_id);
}

export const getTileFeatureById = (layer: geo.layer, featureId: number, type='annotation') => {
    return layer.features().find((f: any) => {
        return f.featureType === 'polygon' && f.props.tile_id === featureId && f.props.type === type;
    });
}

export const tileIdIsValid = (tileId: number | null | undefined) => {
    if (tileId === null || tileId === undefined) {
        console.warn('Tile ID is invalid:', tileId);
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

export const createGTTileFeature = (featureProps: any, annotations: Annotation[], layer: any, annotationClass: AnnotationClass, currentAnnotationId: number | null = null,) => {
    const feature = layer.createFeature('polygon');
    const color = annotationClass.color;
    feature.props = featureProps;
    featureProps.type = 'annotation';

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
                return ann.id === options.currentAnnotationId? 'black' : 'white';
            });
        } else  {
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