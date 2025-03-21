import geo from "geojs"
import { Point, Polygon, Feature, Position, GeoJsonGeometryTypes } from "geojson";
import { Annotation } from "../types";

export const computeTilesToRender = (oldTileIds: number[], newTileIds: number[]) => {
    const a = new Set(oldTileIds)
    const b = new Set(newTileIds)
    const tilesToRemove = new Set([...a].filter(x => !b.has(x)));
    const tilesToRender = new Set([...b].filter(x => !a.has(x)));
    return { tilesToRemove, tilesToRender }
}

export const getTileFeatureById = (layer: geo.layer, feature_id: number) => {
    return layer.features().find((f: any) => {
        return f.featureType === 'polygon' && f.props.tile_id === feature_id;
    });
}

export const redrawTileFeature = (feature: any, options = {}, data?: Annotation[]) => {
    if (data) {
        feature.data(data);
    }
    console.log(`redrew feature ${feature}`)
    feature.modified();
    feature.draw(options);
}

export const createGTTileFeature = (featureProps: any, annotations: Annotation[], layer: any, currentAnnotationId: number | null = null, annotationClassId: number = 1) => {
    const feature = layer.createFeature('polygon');
    feature.props = featureProps;

    feature
        .position((d: Position) => ({ x: d[0], y: d[1] }))
        .polygon((a: Annotation) => a.parsedPolygon.coordinates[0])
        .data(annotations)
        .style('fill', true)
        .style('fillColor', 'lime')
        .style('fillOpacity', 0.5)
        .style('strokeColor', 'black')
        .style('strokeWidth', 2)
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


export const createPredTileFeature = (featureProps: any, annotations: Annotation[], layer: any, highlightedPolyIds: number[] | null = null, annotationClassId: number = 1) => {
    const feature = layer.createFeature('polygon');
    feature.props = featureProps;
    feature
        .position((d: Position) => ({ x: d[0], y: d[1] }))
        .polygon((a: Annotation) => a.parsedPolygon.coordinates[0])
        .data(annotations)
        .style('fill', true)
        .style('fillColor', 'lime')
        .style('fillOpacity', 0.5)
        .style('strokeColor', 'red')
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
    console.log('Drew predicted polygons.')
    feature.draw({ highlightedPolyIds: highlightedPolyIds });
    return feature;
}
