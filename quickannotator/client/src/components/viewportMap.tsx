import React, { useEffect, useState, useRef } from 'react';
import geo from "geojs"
import { Annotation, Image, AnnotationClass, Tile, CurrentAnnotation } from "../types.ts"
import { fetchTile, searchTiles, searchAnnotations, fetchAllAnnotations, postAnnotation, operateOnAnnotation, putAnnotation, removeAnnotation, searchAnnotationsWithinTile, predictTile } from "../helpers/api.ts";
import { Point, Polygon, Feature } from "geojson";
import { responsivePropType } from 'react-bootstrap/esm/createUtilityClasses';


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

const layerIdxNames = {
    gt: 0,
    pred: 1,
    osm: 2,
    ann: 3
}

const ViewportMap = (props: Props) => {
    const viewRef = useRef(null);
    // const [dlTileQueue, setDlTileQueue] = useState<Tile[] | null>(null);
    const geojs_map = useRef<geo.map | null>(null);
    const polygonClicked = useRef<Boolean>(false);  // We need this to ensure polygon clicked and background clicked are mutually exclusive, because geojs does not provide control over event propagation.
    const activeRenderGroundTruthsCall = useRef<number>(0);
    const activeRenderPredictionsCall = useRef<number>(0);
    let zoomPanTimeout: any = null;

    const renderAnnotations = async (
        x1: number, y1: number, x2: number, y2: number, 
        activeCallRef: React.MutableRefObject<number>, is_gt: boolean
    ) => {
        if (!props.currentImage || !props.currentClass) return;

        const currentCallToken = ++activeCallRef.current;
        const tiles = await searchTiles(props.currentImage.id, props.currentClass.id, x1, y1, x2, y2);  // Tiles may be shared by both layers. Consider pushing this to a shared state.
        const layerIdx = is_gt ? layerIdxNames.gt : layerIdxNames.pred;
        const layer = geojs_map.current.layers()[layerIdx];

        const tilesRendered = layer.features()
            .filter((f) => f.featureType === 'polygon')
            .map((f) => f.props.tileId);
        const { tilesToRemove, tilesToRender } = computeTilesToRender(tilesRendered, tiles.map((t) => t.id));

        console.log(`Tiles to remove: ${tilesToRemove.size}`);
        tilesToRemove.forEach((tileId) => {
            const feature = getFeatureByTileId(layerIdx, tileId);
            if (feature) {
                feature.data([]);
                layer.removeFeature(feature);
                feature.draw();
                console.log(`Removed tile ${tileId}`);
            }
        });

        let renderFunction;
        let setAnnotations;

        if (is_gt) {
            renderFunction = processGroundTruthTile;
            setAnnotations = props.setGts;
        } else {
            renderFunction = processPredictedTile;
            setAnnotations = props.setPreds;
        }

        let anns: Annotation[] = [];
        for (const tile of tiles) {     // For all tiles within the current viewport bounds
            if (tilesToRender.has(tile.id)) {   // Tile is not yet rendered
                if (currentCallToken !== activeCallRef.current) {
                    console.log("Render cancelled.");
                    return;
                }
                console.log(`Processing tile ${tile.id}`);
                const resp = await searchAnnotationsWithinTile(tile, is_gt);
                if (currentCallToken !== activeCallRef.current) {
                    console.log("Render cancelled.");
                    return;
                }
                // anns.push(...resp);
                anns = anns.concat(resp);
                renderFunction(tile, resp, layer);
            } else {    // Tile is already rendered
                const data: Annotation[] = getFeatureByTileId(layerIdx, tile.id)?.data();
                // anns.push(...data);
                anns = anns.concat(data);
            }
            setAnnotations(anns);
        }
    };

    const processPredictedTile = (tile: Tile, annotations: Annotation[], layer: any) => {
        switch (tile.seen) {
            case 0:
                // call compute endpoint
                predictTile(tile.id).then((resp) => {
                    console.log("Predicting tile. Ray object ref: ", resp.object_ref);
                })
                console.log("Tile not seen.");

                break;
            case 1:
                // do nothing
                console.log("Tile currently processing.");
                break;
            case 2:
                console.log("Tile seen.");
                drawPredictedPolygons({ tileId: tile.id }, annotations, layer);
                break;
            default:
                console.log("Invalid tile seen value.");
                break;
        }
    };

    const processGroundTruthTile = (tile: Tile, annotations: Annotation[], layer: any) => {
        const featureProps = { tileId: tile.id };
        drawGroundTruthPolygons(featureProps, annotations, layer);
    }

    const renderTissueMask = async (map: geo.map) => {
        if (!props.currentImage || !props.currentClass) return;
        const resp = await fetchAllAnnotations(props.currentImage.id, props.currentClass.id, true);
        drawGroundTruthPolygons({}, resp, map);
        props.setGts(resp);
    }

    const drawGroundTruthPolygons = async (featureProps: any, annotations: Annotation[], layer: any, annotationClassId: number=1) => {
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
        console.log('Drew ground truth polygons.')
    }

    const drawPredictedPolygons = async (featureProps: any, annotations: Annotation[], layer: any, annotationClassId: number=1) => {
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
            .style('fillColor', 'red')
            .style('fillOpacity', 0.5)
            .style('stroke', false)
            .draw();
        console.log('Drew predicted polygons.')
    }

    const drawCentroids = (annotations: Annotation[], map: geo.map) => {
        return;
    }

    const getFeatureByTileId = (layerIdxNames: number, tileId: number) => {
        return geojs_map.current.layers()[layerIdxNames].features().find((f) => {
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
                const oldFeature = getFeatureByTileId(layerIdxNames.gt, props.currentAnnotation.current.tileId);
                
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

            const feature = getFeatureByTileId(layerIdxNames.gt, ann.tileId);
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
                const feature = getFeatureByTileId(layerIdxNames.gt, ann.tileId);
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
        const polygonLayer = geojs_map.current.layers()[layerIdxNames.gt];
        const annotationLayer = geojs_map.current.layers()[layerIdxNames.ann];
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
                const feature = getFeatureByTileId(layerIdxNames.gt, ann.tileId);
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
                            const feature = getFeatureByTileId(layerIdxNames.gt, tileId);
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

    const handleZoomPan = () => {
        console.log('Zooming or Panning...');
        // Clear the previous timeout if the zoom continues
        if (zoomPanTimeout) clearTimeout(zoomPanTimeout);
        // Set a new timeout to detect when zooming has stopped
        zoomPanTimeout = setTimeout(() => {
            console.log('Zooming or Panning stopped.');
            const bounds = geojs_map.current.bounds();
            console.log(bounds);

            renderAnnotations(bounds.left, bounds.bottom, bounds.right, bounds.top, activeRenderGroundTruthsCall, true).then(() => {
                console.log("Ground truths rendered.");
            });
            renderAnnotations(bounds.left, bounds.bottom, bounds.right, bounds.top, activeRenderPredictionsCall, false).then(() => {
                console.log("Predictions rendered.");
            });
        }, 100); // Adjust this timeout duration as needed
    };

    useEffect(() => {
        const interval = setInterval(() => {
            console.log("Interval triggered.");
            if (geojs_map.current && props.currentImage && props.currentClass) {
                const bounds = geojs_map.current.bounds();
                renderAnnotations(bounds.left, bounds.bottom, bounds.right, bounds.top, activeRenderPredictionsCall, false).then(() => {
                    console.log("Predictions rendered.");
                });
            }
        }, 500);

        return () => clearInterval(interval); // Cleanup on unmount
    }, [props.currentClass]);

    // UseEffect hook to initialize the map
    useEffect(() => {
        const initializeMap = async () => {
            const img = props.currentImage;

            // if (img && props.currentClass) {
            const params = geo.util.pixelCoordinateParams(
                viewRef.current, img.width, img.height, img.dz_tilesize, img.dz_tilesize);
            const interactor = geo.mapInteractor({alwaysTouch: true});
            const map = geo.map({...params.map, interactor: interactor});
            // map.interactor(geo.mapInteractor({alwaysTouch: true}))
            map.geoOn(geo.event.mousedown, function (evt) {
                const t = this;
            });
            params.layer.url = `/api/v1/image/${img.id}/patch_file/{z}/{x}_{y}.png`;
            console.log("OSM layer loaded.");
            const groundTruthLayer = map.createLayer('feature', {features: ['polygon']});
            const predictionsLayer = map.createLayer('feature', {features: ['polygon']});
            map.createLayer('osm', { ...params.layer, zIndex: 0 })
            const annotationLayer = map.createLayer('annotation', 
                {
                    active: true, 
                    zIndex: 2,
                    // renderer: featureLayer.renderer()
                });
            annotationLayer.geoOn(geo.event.mousedown, handleMousedown);
            annotationLayer.geoOn(geo.event.annotation.state, handleNewAnnotation);
            window.onkeydown = (evt) => {
                if (evt.key === 'Backspace' || evt.key === 'Delete') {
                    deleteAnnotation(evt);;
                }
            }

            // map.geoOn(geo.event.mousemove, function (evt: any) {console.log(`Mouse at x=${evt.geo.x}, y=${evt.geo.y}`);});
            map.geoOn(geo.event.zoom, handleZoomPan);
            if (props.currentClass.id === 1) {      // Tissue mask class requires different rendering approach.
                renderTissueMask(map).then(() => console.log("Tissue mask rendered."));
            } else {
                map.geoOn(geo.event.pan, handleZoomPan);
            }
            geojs_map.current = map;
            return null;
        }

        if (props.currentImage && props.currentClass) {
            // Need code to clear the map
            activeRenderGroundTruthsCall.current = 0;
            geojs_map.current?.exit();
            initializeMap().then(() => console.log(`Map initialized for ${geojs_map.current}`));
        }

    }, [props.currentImage, props.currentClass]);

    // UseEffect for when the toolbar value changes
    useEffect(() => {
        console.log('detected toolbar change');
        const layer = geojs_map.current?.layers()[layerIdxNames.ann];
        switch (props.currentTool) {
            case null:
                console.log("toolbar is null");
                break;
            case '0':   // Pointer tool
                console.log("toolbar is 0");
                layer?.mode(null);
                break;
            case '5':   // polygon tool
                // layer.active(true)
                layer.mode('polygon');
                break;
            default:

                break;

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