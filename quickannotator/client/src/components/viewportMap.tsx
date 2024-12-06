import React, { useEffect, useState, useRef } from 'react';
import geo from "geojs"
import { Annotation, Image, AnnotationClass, Tile, CurrentAnnotation } from "../types.ts"
import { fetchTile, searchTiles, searchAnnotations, fetchAllAnnotations, postAnnotation, operateOnAnnotation, putAnnotation, removeAnnotation } from "../helpers/api.ts";
import { Point, Polygon, Feature } from "geojson";


interface Props {
    currentImage: Image | null;
    currentClass: AnnotationClass | null;
    currentAnnotation: React.MutableRefObject<CurrentAnnotation | null>;
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
    const polygonClicked = useRef<Boolean>(false);  // We need this to ensure polygon clicked and background clicked are mutually exclusive, because geojs does not provide control over event propagation.
    const activeRenderAnnotationsCall = useRef<number>(0);
    let zoomPanTimeout = null;

    const renderAnnotations = async (x1: number, y1: number, x2: number, y2: number) => {
        if (!props.currentImage || !props.currentClass) return;
        const currentCallToken = ++activeRenderAnnotationsCall.current;
        // need a loop here across all classes
        const tiles = await searchTiles(props.currentImage.id, props.currentClass.id, x1, y1, x2, y2)

        // compute the difference between tiles and tiles_in_view
        const tilesRendered = geojs_map.current.layers()[0].features()
            .filter((f) => f.featureType === 'polygon')
            .map((f) => f.props.tileId);
        const {tilesToRemove, tilesToRender} = computeTilesToRender(tilesRendered, tiles.map((t) => t.id));
        let anns: Annotation[] = [];

        // remove old tiles
        const layer = geojs_map.current.layers()[0];
        console.log(`Tiles to remove: ${tilesToRemove.size}`)
        tilesToRemove.forEach((tileId) => {
            const feature = layer.features().find((f) => {
                return f.featureType === 'polygon' && f.props.tileId === tileId
            });
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
        const geom = JSON.parse(t.geom.toString());
        // const tileState = t.seen;

        const x1 = Math.round(geom.coordinates[0][0][0]);
        const y1 = Math.round(geom.coordinates[0][0][1]);
        const x2 = Math.round(geom.coordinates[0][2][0]);
        const y2 = Math.round(geom.coordinates[0][2][1]);

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

    const drawPolygons = async (featureProps, annotations: Annotation[], map: geo.map, annotationClassId: number=1) => {
        console.log("Annotations detected update.")
        const layer = map.layers()[0];

        const feature = layer.createFeature('polygon');
        feature.props = featureProps;

        feature
            .position((d) => {
                return {
                x: d[0], y: d[1]};
            })
            .polygon((a: Annotation) => {
                const polygon = JSON.parse(a.polygon.toString());
                return polygon.coordinates[0];
            })
            .data(annotations)
            .style('fill', true)
            .style('fillColor', 'lime')
            .style('fillOpacity', 0.5)
            .style('stroke', (a: Annotation) => {
                if (a.id === props.currentAnnotation.current?.undoStack.at(-1)?.id) {
                    console.log("Change stroke of polygon.")    // For some reason this is getting called many times.
                    return true
                }
                return false; // Default to no stroke
            })
            .style('strokeColor', 'black')
            .style('strokeWidth', 2)
            .geoOn(geo.event.feature.mousedown, handleMousedownOnPolygon).draw();
        console.log('Drew polygon')
    }

    const drawCentroids = (annotations: Annotation[], map: geo.map) => {
        console.log("Annotations detected update.")
        const layer = map.layers()[0];
        const feature = layer.features()[1];

        const newData = annotations.map((a) => {
            const centroid = JSON.parse(a.centroid.toString());
            return centroid.coordinates;
        });

        feature
            .position((d) => {return {
                x: d[0], y: d[1]};
            })
            .style('stroke', false)
            .style('size', 1)
            .data(feature.data().concat(newData)).draw();
    }

    const getFeatureByTileId = (tileId: number) => {
        return geojs_map.current.layers()[0].features().find((f) => {
            return f.featureType === 'polygon' && f.props.tileId === tileId;
        });
    }

    function handleMousedownOnPolygon(evt) {    // TODO: Clean up this function. There is redundant code.
        console.log("Polygon clicked.")
        console.log(evt.data)
        polygonClicked.current = true;

        if(props.currentAnnotation.current) {   // If the current annotation exists, 
            if (props.currentAnnotation.current.undoStack.at(-1)?.id !== evt.data.id) {   // If the current annotation id has changed...
                // Commit the previously selected annotation
                putAnnotation(props.currentImage.id, props.currentClass.id, props.currentAnnotation.current.undoStack.at(-1))

                // Get the old feature
                const oldFeature = getFeatureByTileId(props.currentAnnotation.current.tileId);
                
                // Set the current annotation to the clicked annotation
                const clickedAnnotation: CurrentAnnotation = {
                    tileId: this.props.tileId,
                    redoStack: [],
                    undoStack: [evt.data]
                }

                props.currentAnnotation.current = clickedAnnotation;

                this.modified();
                this.draw();

                if (oldFeature.props.tileId !== this.props.tileId) {
                    // feature.data([evt.data]);
                    console.log(`redrew feature ${oldFeature}`)
                    oldFeature.modified();
                    oldFeature.draw();
                }

            }
        } else {

            const clickedAnnotation: CurrentAnnotation = {
                id: evt.data.id,
                tileId: this.props.tileId,
                redoStack: [],
                undoStack: [evt.data]
            }

            props.currentAnnotation.current = clickedAnnotation;

            this.modified();
            this.draw();
        }
        setTimeout(() => {
            polygonClicked.current = false;
        }, 0);
    }

    function handleMousedown(evt) {
        console.log("Mouse down detected.")
        if (!polygonClicked.current && props.currentAnnotation.current) {
            const ann = props.currentAnnotation.current;
            putAnnotation(props.currentImage.id, props.currentClass.id, ann.undoStack.at(-1))

            const feature = getFeatureByTileId(ann.tileId);
            props.currentAnnotation.current = null;
            feature.modified();
            feature.draw();

            console.log("Background clicked - committed current annotation.")
        }
    }

    function deleteAnnotation(evt) {
        console.log("Delete annotation detected.")
        const ann = props.currentAnnotation.current;
        const image = props.currentImage;
        const annotationClass = props.currentClass;
        const annotationId = ann?.undoStack.at(-1).id;
        if (annotationId && image && annotationClass) {
            removeAnnotation(image.id, annotationClass.id, annotationId, true).then(() => {
                const feature = getFeatureByTileId(ann.tileId);
                const data = feature.data();
                const deletedData = data.filter((d: Annotation) => {
                    return d.id !== annotationId;
                });
                feature.data(deletedData);
                feature.modified();
                feature.draw();
                props.currentAnnotation.current = null;
                console.log(`Annotation id=${annotationId} deleted.`)
            })
        }
    }

    const handleNewAnnotation = async (evt) => {
        console.log("New annotation detected.")
        const polygonLayer = geojs_map.current.layers()[0]
        const annotationLayer = geojs_map.current.layers()[2]
        const polygonList = annotationLayer.toPolygonList()[0][0].map((p: number[]) => {    // This is a hack to convert the polygon to the correct coordinate space.
            return [p[0], -p[1]]
        })  

        if (polygonList.length > 0 && props.currentImage && props.currentClass) {
            // 1. Get the polygon from the annotation layer.
            const polygon2: Polygon = {
                type: "Polygon",
                coordinates: [polygonList]
            }

            const ann = props.currentAnnotation.current;

            // 2. if currentAnnotation exists, update the currentAnnotation
            if (ann) {
                console.log("Current annotation exists. Updating...")
                // // 1. Get the feature data associated with the CurrentAnnotation
                const feature = getFeatureByTileId(ann.tileId);
                const data = feature.data();
                const currentState = ann.undoStack.pop();
                ann.redoStack.push(currentState);
                operateOnAnnotation(currentState, polygon2, 0).then((newState) => {
                    ann.undoStack.push(newState);

                    const updatedData = data.map((d: Annotation) => {
                        if (d.id === ann.id) {
                            return newState;
                        }
                        return d;
                    });

                    feature.data(updatedData);
                    feature.modified();
                    feature.draw();
                });

            } else {    // if currentAnnotation does not exist, create a new annotation
                console.log("Current annotation does not exist. Creating...")
                postAnnotation(props.currentImage.id, props.currentClass.id, true, polygon2).then((resp) => {
                    const xy = JSON.parse(resp.centroid).coordinates;
                    searchTiles(props.currentImage?.id, props.currentClass?.id, xy[0], xy[1], xy[0], xy[1]).then((tiles) => {
                        if (tiles.length > 0) {
                            const tileId = tiles[0].id;
                            const feature = getFeatureByTileId(tileId);
                            const data = feature.data();
                            const updatedData = data.concat(resp);
                            feature.data(updatedData);
                            feature.modified();
                            feature.draw();
                        }
                    });
                });
            
            }

            const mode = annotationLayer.mode();
            annotationLayer.mode(null);
            annotationLayer.removeAllAnnotations();
            annotationLayer.mode(mode);
            
            console.log("Annotation layer cleared.")
        }

        // polygonFeature.data(polygonList).draw()
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

            // if (img && props.currentClass) {
            const params = geo.util.pixelCoordinateParams(
                viewRef.current, img.width, img.height, img.dz_tilesize, img.dz_tilesize);
            const interactor = geo.mapInteractor({alwaysTouch: true})
            const map = geo.map({...params.map, interactor: interactor});
            // map.interactor(geo.mapInteractor({alwaysTouch: true}))
            map.geoOn(geo.event.mousedown, function (evt) {
                const t = this;
            });
            params.layer.url = `/api/v1/image/${img.id}/patch_file/{z}/{x}_{y}.png`;
            console.log("OSM layer loaded.")
            const featureLayer = map.createLayer('feature', {features: ['polygon']});
            map.createLayer('osm', { ...params.layer, zIndex: 0 })
            const annotationLayer = map.createLayer('annotation', 
                {
                    active: true, 
                    zIndex: 2,
                    // renderer: featureLayer.renderer()
                });
            annotationLayer.geoOn(geo.event.mousedown, handleMousedown)
            annotationLayer.geoOn(geo.event.annotation.state, handleNewAnnotation)
            window.onkeydown = (evt) => {
                if (evt.key === 'Backspace' || evt.key === 'Delete') {
                    deleteAnnotation(evt);
                }
            }

            // map.geoOn(geo.event.mousemove, function (evt: any) {console.log(`Mouse at x=${evt.geo.x}, y=${evt.geo.y}`);});
            map.geoOn(geo.event.zoom, handleZoomPan)
            if (props.currentClass.id === 1) {      // Tissue mask class requires different rendering approach.
                renderTissueMask(map).then(() => console.log("Tissue mask rendered."));
            } else {
                map.geoOn(geo.event.pan, handleZoomPan)
            }
            geojs_map.current = map;
            return null;
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