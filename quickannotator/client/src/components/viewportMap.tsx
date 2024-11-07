import React, { useEffect, useState, useRef } from 'react';
import geo from "geojs"
import { Annotation, Image, AnnotationClass, Tile } from "../types.ts"
import { fetchTile, searchTiles, searchAnnotations, fetchAllAnnotations } from "../helpers/api.ts";

interface Props {
    currentImage: Image | null;
    currentClass: AnnotationClass | null;
    gts: Annotation[];
    setGts: (gts: Annotation[]) => void;
    preds: Annotation[];
    setPreds: (preds: Annotation[]) => void;
    currentTool: string | null;
}

const computeTilesToRender = (oldTileIds: number[], newTileIds: number[]) => {
    const a = new Set(oldTileIds)
    const b = new Set(newTileIds)
    const tilesToRemove = new Set([...a].filter(x => !b.has(x)));
    const tilesToRender = new Set([...b].filter(x => !a.has(x)));
    return {tilesToRemove, tilesToRender}
}

const ViewportMap = (props: Props) => {
    const viewRef = useRef(null);
    // const [dlTileQueue, setDlTileQueue] = useState<Tile[] | null>(null);
    const geojs_map = useRef<geo.map | null>(null);
    const activeRenderAnnotationsCall = useRef<number>(0);
    let zoomPanTimeout = null;

    const renderAnnotations = async (x1: number, y1: number, x2: number, y2: number) => {
        if (!props.currentImage || !props.currentClass) return;
        const currentCallToken = ++activeRenderAnnotationsCall.current;
        const tiles = await searchTiles(props.currentImage.id, props.currentClass.id, x1, y1, x2, y2)
        // compute the difference between tiles and tiles_in_view
        const tilesRendered = geojs_map.current.layers()[0].features().map((f) => f.props.tileId);
        const {tilesToRemove, tilesToRender} = computeTilesToRender(tilesRendered, tiles.map((t) => t.id));
        let anns = [];

        // remove old tiles
        const layer = geojs_map.current.layers()[0];
        console.log(`Tiles to remove: ${tilesToRemove.size}`)

        tilesToRemove.forEach((tileId) => {
            const feature = layer.features().find((f) => f.props.tileId === tileId);
            if (feature) {
                feature.data([]);
                layer.removeFeature(feature);
                feature.draw();
                console.log(`Removed tile ${tileId}`)
            }
        });

        // render new tiles
        for (const tile of tiles) {
            if (tilesToRender.has(tile.id)) {
                if (currentCallToken !== activeRenderAnnotationsCall.current) {     // We want to check before processing the tile to save resources
                    console.log("Render cancelled.")
                    return;
                }
                console.log(`Processing tile ${tile.id}`)
                const resp = await processTile(tile);
                if (currentCallToken !== activeRenderAnnotationsCall.current) {     // ... and after processing the tile to avoid the race condition
                    console.log("Render cancelled.")
                    return;
                }
                const featureProps = {
                    tileId: tile.id
                }
                drawPolygons(featureProps, resp, geojs_map.current);
                // drawCentroids(resp, geojs_map.current);
                anns = anns.concat(resp);
                props.setGts(anns);
            }
        }



    }

    const renderTissueMask = async (map: geo.map) => {
        if (!props.currentImage || !props.currentClass) return;
        const resp = await fetchAllAnnotations(props.currentImage.id, props.currentClass.id, true);
        drawPolygons({}, resp, map);
        props.setGts(resp);
    }

    const processTile = async (tile: Tile) => {
        const t = await fetchTile(tile.id);
        const geom = JSON.parse(t.geom.toString());    // for some reason the geom is stringified
        // const tileState = t.seen;

        const x1 = geom.geometry.coordinates[0][0][0];
        const y1 = geom.geometry.coordinates[0][0][1];
        const x2 = geom.geometry.coordinates[0][2][0];
        const y2 = geom.geometry.coordinates[0][2][1];

        // switch (tileState) {
        //     case 0:
        //         console.log("Tile not seen");
        //         /*  Tile not seen. Perform the following:
        //         *   1. Call compute endpoint
        //         *   2. Update tile state to 1
        //         *   3. Update Queue with tile
        //         * */
        //         break;
        //     case 1:
        //         console.log("Tile processing");
        //         /*  Tile processing. Perform the following:
        //         *   1. Push tile to end of queue
        //          */
        //         break;
        //     case 2:
        //         console.log("Tile processed");
        //         searchAnnotations(t.image_id, t.annotation_class_id, false, x1, y1, x2, y2).then((annotations) => {
        //             console.log("Predictions")
        //             console.log(annotations);
        //         });
        //         break;
        //
        // }

        const resp = await searchAnnotations(t.image_id, t.annotation_class_id, true, x1, y1, x2, y2)
        return resp
    }

    const drawPolygons = async (featureProps, annotations: Annotation[], map: geo.map) => {
        console.log("Annotations detected update.")
        const layer = map.layers()[0];
        const feature = layer.createFeature('polygon');
        feature.props = featureProps;
        const newData = annotations.map((a) => {
            const polygon = JSON.parse(a.polygon.toString());
            return polygon.geometry.coordinates[0];
        });

        feature
            .position((d) => {
                const m = ""
                return {
                x: d[0], y: d[1]};
            })
            .polygon((a: Annotation) => {
                const polygon = JSON.parse(a.polygon.toString());   // shouldn't be doing json parsing here.
                return polygon.geometry.coordinates[0];
            }) //should return the polygon.geometry.coordinates[0];
            .data(annotations)
            .style('fill', 'lime')
            .style('fillOpacity', 0.5)
            .style('stroke', false)
            .geoOn(geo.event.feature.mouseclick, function (evt: any) {
                console.log(evt.data);
            }).draw();
    }

    const drawCentroids = (annotations: Annotation[], map: geo.map) => {
        console.log("Annotations detected update.")
        const layer = map.layers()[0];
        const feature = layer.features()[1];

        const newData = annotations.map((a) => {
            const centroid = JSON.parse(a.centroid.toString());
            return centroid.geometry.coordinates;
        });

        feature
            .position((d) => {return {
                x: d[0], y: d[1]};
            })
            .style('stroke', false)
            .style('size', 1)
            .data(feature.data().concat(newData)).draw();
    }

    const handleNewAnnotation = (evt) => {
        const polygonLayer = geojs_map.current.layers()[0]
        const annotationLayer = geojs_map.current.layers()[2]
        const polygonList = annotationLayer.toPolygonList()
        const polygonFeature = polygonLayer.features()[0]
        if (!evt.mode && evt.oldMode == 'polygon') {
            annotationLayer.mode('polygon')
        }

        polygonFeature.data(polygonList).draw()
    }

    // UseEffect hook to initialize the map
    useEffect(() => {
        const handleZoomPan = () => {
            console.log('Zooming or Panning...');
            // Clear the previous timeout if the zoom continues
            if (zoomPanTimeout) clearTimeout(zoomPanTimeout);
            // Set a new timeout to detect when zooming has stopped
            zoomPanTimeout = setTimeout(() => {
                console.log('Zooming or Panning stopped.');
                const bounds = geojs_map.current.bounds();
                console.log(bounds);

                renderAnnotations(bounds.left, bounds.bottom, bounds.right, bounds.top).then(() => {
                    console.log("Annotations rendered.");
                });
                // renderAnnotationTest();
            }, 100); // Adjust this timeout duration as needed
        };

        const initializeMap = async () => {
            const img = props.currentImage;

            if (img && props.currentClass) {
                const params = geo.util.pixelCoordinateParams(
                    viewRef.current, img.width, img.height, img.dz_tilesize, img.dz_tilesize);
                const interactor = geo.mapInteractor({alwaysTouch: true})
                const map = geo.map({...params.map, interactor: interactor});
                // map.interactor(geo.mapInteractor({alwaysTouch: true}))

                params.layer.url = `/api/v1/image/${img.id}/patch_file/{z}/{x}_{y}.png`;
                console.log("OSM layer loaded.")
                map.createLayer('feature', {features: ['polygon']});
                map.createLayer('osm', { ...params.layer, zIndex: 0 })
                const annotationLayer = map.createLayer('annotation', {active: true, zIndex: 2});
                annotationLayer.geoOn(geo.event.annotation.mode, handleNewAnnotation)


                map.geoOn(geo.event.mousemove, function (evt: any) {
                    console.log(`Mouse at x=${evt.geo.x}, y=${evt.geo.y}`);
                });
                map.geoOn(geo.event.zoom, handleZoomPan)
                if (props.currentClass.id === 1) {      // Tissue mask class requires different rendering approach.
                    renderTissueMask(map).then(() => console.log("Tissue mask rendered."));
                } else {
                    map.geoOn(geo.event.pan, handleZoomPan)
                }
                geojs_map.current = map;
                return null;
            }
        }

        if (props.currentImage && props.currentClass) {
            // Need code to clear the map
            activeRenderAnnotationsCall.current = 0;
            geojs_map.current?.exit();
            initializeMap().then(() => console.log(`Map initialized for ${geojs_map.current}`));
        }

    }, [props.currentImage, props.currentClass]);

    // UseEffect for when the toolbar value changes
    useEffect(() => {
        console.log('detected toolbar change')
        const layer = geojs_map.current?.layers()[2];
        switch (props.currentTool) {
            case null:
                console.log("toolbar is null")
                break;
            case '0':   // Pointer tool
                console.log("toolbar is 0")
                layer?.mode(null)
                break
            case '5':   // polygon tool
                // layer.active(true)
                layer.mode('polygon')
                break
            default:

                break

        }
    }, [props.currentTool])
    return (
        <div ref={viewRef} style={
            {
                width: '100%',
                height: '100%',
                backgroundColor: 'white',
                borderRadius: 6
            }
        }>
        </div>
    )
}

export default ViewportMap;