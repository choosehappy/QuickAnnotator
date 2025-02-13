import geo from "geojs"
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
