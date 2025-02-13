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

export const getTileFeatureById = (geoMap: geo.map, layerId: number, tile_id: number) => {
    return geoMap.current.layers()[layerId].features().find((f) => {
        return f.featureType === 'polygon' && f.props.tile_id === tile_id;
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

export const createGTTileFeature = (featureProps: any, annotations: Annotation[], layer: any, currentAnnotationId: number, annotationClassId: number = 1) => {
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

    const originalDraw = feature.draw;
    // Override the draw method to accept options.
    feature.draw = (options = { currentAnnotationId: null }) => {
        feature.style('stroke', (a: Annotation) => {
            return a.id === options.currentAnnotationId
        });
        originalDraw.call(feature);
    }
    console.log('Drew ground truth polygons.')
    feature.draw({ currentAnnotationId: currentAnnotationId });
    return feature;
}

export const createPredTileFeature = (featureProps: any, annotations: Annotation[], layer: any, annotationClassId: number = 1) => {
    const feature = layer.createFeature('polygon');
    feature.props = featureProps;
    feature
        .position((d: Position) => ({ x: d[0], y: d[1] }))
        .polygon((a: Annotation) => a.parsedPolygon.coordinates[0])
        .data(annotations)
        .style('fill', true)
        .style('fillColor', 'lime')
        .style('fillOpacity', 0.5)
        .style('stroke', true)
        .style('strokeColor', 'white')
        .draw();
    console.log('Drew predicted polygons.')
    return feature;
}
