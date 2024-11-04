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

const ViewportMap = (props: Props) => {
    const viewRef = useRef(null);
    // const [dlTileQueue, setDlTileQueue] = useState<Tile[] | null>(null);
    const geojs_map = useRef<geo.map | null>(null);
    const activeRenderAnnotationsCall = useRef<number>(0);
    let zoomPanTimeout = null;

    async function renderAnnotations(x1: number, y1: number, x2: number, y2: number) {
        if (!props.currentImage || !props.currentClass) return;
        const currentCallToken = ++activeRenderAnnotationsCall.current;
        const tiles = await searchTiles(props.currentImage.id, props.currentClass.id, x1, y1, x2, y2)

        let anns = [];
        for (const tile of tiles) {
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
            drawPolygons(resp, geojs_map.current);
            // drawCentroids(resp, geojs_map.current);
            anns = anns.concat(resp);
            props.setGts(anns);
        }
    }

    async function renderTissueMask(map: geo.map) {
        if (!props.currentImage || !props.currentClass) return;
        const resp = await fetchAllAnnotations(props.currentImage.id, props.currentClass.id, true);
        drawPolygons(resp, map);
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

    const drawPolygons = async (annotations: Annotation[], map: geo.map) => {
        console.log("Annotations detected update.")
        const layer = map.layers()[0];
        const feature = layer.features()[0];

        const newData = annotations.map((a) => {
            const polygon = JSON.parse(a.polygon.toString());
            return polygon.geometry.coordinates[0];
        });

        feature
            .position((d) => {return {
                x: d[0], y: d[1]};
            })
            // .polygon() should return the polygon.geometry.coordinates[0];
            .data(feature.data().concat(newData))
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
                const layer = geojs_map.current.layers()[0];
                const polygonFeature = layer.features()[0];
                const pointFeature = layer.features()[1];

                layer.deleteFeature(polygonFeature);
                layer.createFeature('polygon', {selectionAPI: true});
                layer.deleteFeature(pointFeature);
                layer.createFeature('point')

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
                const map = geo.map(params.map);

                params.layer.url = `/api/v1/image/${img.id}/patch_file/{z}/{x}_{y}.png`;
                console.log("OSM layer loaded.")
                const featureLayer = map.createLayer('feature', {features: ['polygon']});
                featureLayer.createFeature('polygon', {selectionAPI: true});
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