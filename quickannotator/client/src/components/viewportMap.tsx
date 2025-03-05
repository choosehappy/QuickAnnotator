import React, { useEffect, useState, useRef, useCallback } from 'react';
import geo from "geojs"
import { Annotation, Image, AnnotationClass, Tile, CurrentAnnotation, PutAnnArgs, AnnotationResponse } from "../types.ts"
import { searchTiles, fetchAllAnnotations, postAnnotation, operateOnAnnotation, putAnnotation, removeAnnotation, getAnnotationsForTile, predictTile, getAnnotationsWithinPolygon } from "../helpers/api.ts";
import { Point, Polygon, Feature, Position, GeoJsonGeometryTypes } from "geojson";
import { TOOLBAR_KEYS, LAYER_KEYS, TILE_STATUS } from "../helpers/config.ts";
import { computeTilesToRender, getTileFeatureById, redrawTileFeature, createGTTileFeature, createPredTileFeature } from '../utils/map.ts';

interface Props {
    currentImage: Image | null;
    currentClass: AnnotationClass | null;
    currentAnnotation: CurrentAnnotation | null;
    setCurrentAnnotation: React.Dispatch<React.SetStateAction<CurrentAnnotation | null>>;
    prevCurrentAnnotation: CurrentAnnotation | null;
    gts: Annotation[];
    setGts: React.Dispatch<React.SetStateAction<Annotation[]>>;
    preds: Annotation[];
    setPreds: React.Dispatch<React.SetStateAction<Annotation[]>>;
    currentTool: string | null;
    setCurrentTool: React.Dispatch<React.SetStateAction<string | null>>;
    highlightedPreds: Annotation[];
    setHighlightedPreds: React.Dispatch<React.SetStateAction<Annotation[]>>;
}

const useLocalContext = (data: any) => {
    const ctx = React.useRef(data)
    ctx.current = data
    return ctx
}

const ViewportMap = (props: Props) => {
    const viewRef = useRef(null);
    const geojs_map = useRef<geo.map | null>(null);
    const polygonClicked = useRef<Boolean>(false);  // We need this to ensure polygon clicked and background clicked are mutually exclusive, because geojs does not provide control over event propagation.
    const activeRenderGroundTruthsCall = useRef<number>(0);
    const activeRenderPredictionsCall = useRef<number>(0);
    const ctx = useLocalContext({ ...props });
    let zoomPanTimeout: any = null;

    const renderAnnotations = async (
        x1: number, y1: number, x2: number, y2: number,
        activeCallRef: React.MutableRefObject<number>, is_gt: boolean
    ) => {
        if (!props.currentImage || !props.currentClass) return;

        const currentCallToken = ++activeCallRef.current;
        const resp = await searchTiles(props.currentImage.id, props.currentClass.id, x1, y1, x2, y2, !is_gt, is_gt || undefined);  // Tiles may be shared by both layers. Consider pushing this to a shared state.
        const tiles = resp.data;
        const layerIdx = is_gt ? LAYER_KEYS.GT : LAYER_KEYS.PRED;
        const layer = geojs_map.current.layers()[layerIdx];

        const tilesRendered = layer.features()
            .filter((f) => f.featureType === 'polygon')
            .map((f) => f.props.tile_id);
        const { tilesToRemove, tilesToRender } = computeTilesToRender(tilesRendered, tiles.map((t) => t.tile_id));

        // console.log(`Tiles to remove: ${tilesToRemove.size}`);
        tilesToRemove.forEach((tile_id) => {
            const feature = getTileFeatureById(geojs_map, layerIdx, tile_id);
            if (feature) {
                feature.data([]);
                layer.removeFeature(feature);
                feature.draw();
                console.log(`Removed tile ${tile_id}`);
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
            if (tilesToRender.has(tile.tile_id)) {   // Tile is not yet rendered
                if (currentCallToken !== activeCallRef.current) {
                    console.log("Render cancelled.");
                    return;
                }
                console.log(`Processing tile ${tile.tile_id}`);
                const resp = await getAnnotationsForTile(tile.image_id, tile.annotation_class_id, tile.tile_id, is_gt);
                const annotations = resp.data.map(annResp => new Annotation(annResp, props.currentClass.id));
                if (currentCallToken !== activeCallRef.current) {
                    console.log("Render cancelled.");
                    return;
                }
                // anns.push(...resp);
                anns = anns.concat(annotations);
                renderFunction(tile, annotations, layer);
            } else {    // Tile is already rendered
                const data: Annotation[] = getTileFeatureById(geojs_map, layerIdx, tile.tile_id)?.data();
                // anns.push(...data);
                anns = anns.concat(data);
            }
            setAnnotations(anns);
        }
    };

    const processPredictedTile = (tile: Tile, annotations: Annotation[], layer: any) => {
        switch (tile.seen) {
            case TILE_STATUS.UNSEEN:
                // call compute endpoint
                // predictTile(tile.image_id, tile.annotation_class_id, tile.tile_id).then((resp) => {
                //     console.log("Predicting tile. Ray object ref: ", resp.data.object_ref);
                // })
                console.log("Tile not seen.");

                break;
            case TILE_STATUS.STARTPROCESSING:
                // do nothing
                console.log("Tile currently processing.");
                break;
            case TILE_STATUS.PROCESSING:
                // do nothing
                console.log("Tile currently processing.");
                break;
            case TILE_STATUS.DONEPROCESSING:
                console.log("Tile seen.");
                createPredTileFeature({ tile_id: tile.tile_id }, annotations, layer);
                break;
            default:
                console.log("Invalid tile seen value.");
                break;
        }
    };

    const processGroundTruthTile = (tile: Tile, annotations: Annotation[], layer: any) => {
        const featureProps = { tile_id: tile.tile_id };
        const currentAnnotationId = props.currentAnnotation?.currentState?.id;
        const feature = createGTTileFeature(featureProps, annotations, layer, currentAnnotationId, props.currentClass?.id);
        feature.geoOn(geo.event.feature.mousedown, handleMousedownOnPolygon)
    }

    const renderTissueMask = async (map: geo.map) => {  // The renderTissueMask function does not currently work...
        if (!props.currentImage || !props.currentClass) return;
        const resp = await fetchAllAnnotations(props.currentImage.id, props.currentClass.id, true);
        const annotations = resp.data.map(annResp => new Annotation(annResp, props.currentClass.id));
        createGTTileFeature({}, annotations, map);
        props.setGts(annotations);
    }

    const drawCentroids = (annotations: Annotation[], map: geo.map) => {
        return;
    }

    function handleMousedownOnPolygon(evt) {
        console.log("Polygon clicked.")
        console.log(evt.data)
        polygonClicked.current = true;

        props.setCurrentAnnotation(new CurrentAnnotation(evt.data));

        setTimeout(() => {
            polygonClicked.current = false;
        }, 0);
    }

    const handleMousedown = (evt) => {
        const annotationLayer = geojs_map.current.layers()[LAYER_KEYS.ANN];
        const mode = annotationLayer.mode();
        console.log(`Mouse down detected. Mode: ${mode}`);


        console.log(ctx.current.currentAnnotation);
        const currentAnn: CurrentAnnotation = ctx.current.currentAnnotation;
        const currentClass: AnnotationClass = ctx.current.currentClass;
        const currentImage: Image = ctx.current.currentImage;

        if (!polygonClicked.current && currentAnn) {
            const currentState = currentAnn.currentState;
            const tile_id = currentState?.tile_id;
            if (tile_id) {
                props.setCurrentAnnotation(null);
            }
        }
    }

    function handleDeleteAnnotation(evt) {
        console.log("Delete annotation detected.")
        const currentAnn: CurrentAnnotation = ctx.current.currentAnnotation;
        if (!currentAnn) return;    // Delete operation only allowed if an annotation is selected.

        const currentState: Annotation | undefined = currentAnn.currentState;
        const tile_id = currentState?.tile_id;
        const currentImage: Image = ctx.current.currentImage;
        const currentClass: AnnotationClass = ctx.current.currentClass;
        const annotationId = currentState?.id;

        if (annotationId && currentImage && currentClass && tile_id) {
            removeAnnotation(currentImage.id, currentClass.id, annotationId, true).then(() => {
                const feature = getTileFeatureById(geojs_map, LAYER_KEYS.GT, tile_id);
                const data = feature.data();
                const deletedData = data.filter((d: Annotation) => d.id !== annotationId);

                const updatedGroundTruths = ctx.current.gts.filter((gt: Annotation) => gt.id !== annotationId);
                props.setGts(updatedGroundTruths);
                redrawTileFeature(feature, {}, deletedData);
                props.setCurrentAnnotation(null);
                console.log(`Annotation id=${annotationId} deleted.`)
            })
        }
    }

    const updateAnnotation = (currentState: Annotation, newPolygon: Polygon) => {
        const feature = getTileFeatureById(geojs_map, LAYER_KEYS.GT, currentState.tile_id);
        const data = feature.data();
        operateOnAnnotation(currentState, newPolygon, 0).then((resp) => {
            const newState = new Annotation(resp.data, currentState.annotation_class_id);
            const updatedData: Annotation[] = data.map((d: Annotation) => d.id === currentState.id ? newState : d);
            const updatedGroundTruths = ctx.current.gts.map((gt: Annotation) => gt.id === currentState.id ? newState : gt);

            props.setGts(updatedGroundTruths);
            redrawTileFeature(feature, { currentAnnotationId: currentState.id }, updatedData);
        });
    }

    const addAnnotation = (newPolygon: Polygon) => {
        const currentImage: Image = ctx.current.currentImage;
        const currentClass: Annotation = ctx.current.currentClass;

        postAnnotation(currentImage.id, currentClass.id, newPolygon).then((resp) => {
            if (resp.status === 200) {
                const annotation = new Annotation(resp.data, currentClass.id);
                const tile_id = annotation.tile_id;
                if (!tile_id) {
                    console.log("Tile ID not found.")
                    return;
                }
                const feature = getTileFeatureById(geojs_map, LAYER_KEYS.GT, tile_id);
                if (feature) {
                    const data = feature.data();
                    const updatedData = data.concat(annotation);
                    redrawTileFeature(feature, {}, updatedData);
                } else {
                    const feature = createGTTileFeature({}, [annotation], geojs_map.current.layers()[LAYER_KEYS.GT], currentClass.id);
                    feature.geoOn(geo.event.feature.mousedown, handleMousedownOnPolygon);
                }
                props.setGts((prev: Annotation[]) => prev.concat(annotation));
            }
        });
    }

    const handleNewAnnotation = async (evt) => {
        console.log("New annotation detected.")
        const annotationLayer = geojs_map.current.layers()[LAYER_KEYS.ANN];
        const polygonList = annotationLayer.toPolygonList()[0][0].map((p: number[]) => [p[0], -p[1]]);

        const currentImage: Image = ctx.current.currentImage;
        const currentClass: AnnotationClass = ctx.current.currentClass;
        const currentAnn: CurrentAnnotation = ctx.current.currentAnnotation;
        const currentTool: string = ctx.current.currentTool;

        if (!(polygonList.length > 0 && currentImage && currentClass)) {
            console.log("Polygon list is empty.")
            return;
        }

        // Get the polygon from the annotation layer.
        const polygon2: Polygon = { type: "Polygon", coordinates: [polygonList] }

        if (currentTool === TOOLBAR_KEYS.POLYGON) {
            const currentState = currentAnn?.currentState;

            // If currentAnnotation exists, update the currentAnnotation
            if (currentState) {
                console.log("Current annotation exists. Updating...")
                updateAnnotation(currentState, polygon2);

            } else {    // If currentAnnotation does not exist, create a new annotation in the database.
                console.log("Current annotation does not exist. Creating...")
                addAnnotation(polygon2);
            }
        } else if (currentTool === TOOLBAR_KEYS.IMPORT) {
            getAnnotationsWithinPolygon(currentImage.id, currentClass.id, false, polygon2).then((resp) => {
                // get the predicted annotation ids
                if (resp.status === 200) {
                    const anns = resp.data.map((annResp: AnnotationResponse) => new Annotation(annResp, currentClass.id));
                    props.setHighlightedPreds(anns);
                    

                } else {
                    console.log("No annotations found within the polygon.")
                }

            })

            // 2. Highlight these polygons
            // 3. Show a confirmation panel
            // 4. If confirmed, POST the new ground truths and DELETE the predictions.
            // 5. Redraw the respective ground truth and prediction tiles.
            
        }

        // Clear the annotation layer
        annotationLayer.mode(null);
        annotationLayer.removeAllAnnotations();
        console.log("Annotation layer cleared.")
    }

    const handleAnnotationModeChange = (evt) => {
        console.log(`Mode changed from ${evt.oldMode} to ${evt.mode}`);
        const currentTool = ctx.current.currentTool;
        if (evt.mode === null && evt.oldMode === 'polygon' && currentTool !== TOOLBAR_KEYS.POINTER) {
            const annotationLayer = geojs_map.current.layers()[LAYER_KEYS.ANN];
            annotationLayer.mode('polygon');
        }
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
            const x1 = bounds.left;
            const y1 = Math.abs(bounds.top);
            const x2 = bounds.right;
            const y2 = Math.abs(bounds.bottom);
            renderAnnotations(x1, y1, x2, y2, activeRenderGroundTruthsCall, true).then(() => {
                console.log("Ground truths rendered.");
            });
            renderAnnotations(x1, y1, x2, y2, activeRenderPredictionsCall, false).then(() => {
                console.log("Predictions rendered.");
            });
        }, 100); // Adjust this timeout duration as needed
    };

    // UseEffect hook for rendering predictions periodically
    // useEffect(() => {
    //     const interval = setInterval(() => {
    //         // console.log("Interval triggered.");
    //         if (geojs_map.current && props.currentImage && props.currentClass) {
    //             const bounds = geojs_map.current.bounds();
    //             const x1 = bounds.left;
    //             const y1 = Math.abs(bounds.top);
    //             const x2 = bounds.right;
    //             const y2 = Math.abs(bounds.bottom);
    //             renderAnnotations(x1, y1, x2, y2, activeRenderPredictionsCall, false).then(() => {
    //                 console.log("Predictions rendered.");
    //             });
    //         }
    //     }, 500);

    //     return () => clearInterval(interval); // Cleanup on unmount
    // }, [props.currentClass]);

    // UseEffect hook to initialize the map
    useEffect(() => {
        const initializeMap = async () => {
            const img = props.currentImage;

            const params = geo.util.pixelCoordinateParams(
                viewRef.current, img.base_width, img.base_height, img.dz_tilesize, img.dz_tilesize);
            const interactor = geo.mapInteractor({alwaysTouch: true});
            const map = geo.map({...params.map, interactor: interactor});
            // map.interactor(geo.mapInteractor({alwaysTouch: true}))
            params.layer.url = `/api/v1/image/${img.id}/patch_file/{z}/{x}_{y}.png`;
            console.log("OSM layer loaded.");
            const groundTruthLayer = map.createLayer('feature', { features: ['polygon'] });
            const predictionsLayer = map.createLayer('feature', { features: ['polygon'] });
            map.createLayer('osm', { ...params.layer, zIndex: 0 })
            const annotationLayer = map.createLayer('annotation',
                {
                    active: true,
                    zIndex: 2,
                    // renderer: featureLayer.renderer()
                });
            annotationLayer.geoOn(geo.event.mousedown, handleMousedown);
            annotationLayer.geoOn(geo.event.annotation.state, handleNewAnnotation);
            annotationLayer.geoOn(geo.event.annotation.mode, handleAnnotationModeChange);
            window.onkeydown = (evt) => {
                if (evt.key === 'Backspace' || evt.key === 'Delete') {
                    handleDeleteAnnotation(evt);
                }
            }

            map.geoOn(geo.event.mousemove, function (evt: any) { console.log(`Mouse at x=${evt.geo.x}, y=${evt.geo.y}`); });
            map.geoOn(geo.event.zoom, handleZoomPan);
            if (props.currentClass?.id === 1) {      // Tissue mask class requires different rendering approach.
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
        const layer = geojs_map.current?.layers()[LAYER_KEYS.ANN];
        switch (props.currentTool) {
            case null:
                console.log("toolbar is null");
                break;
            case TOOLBAR_KEYS.POINTER:   // Pointer tool
                console.log("toolbar is 0");
                layer?.mode(null);
                break;
            case TOOLBAR_KEYS.POLYGON:   // polygon tool
                // layer.active(true)
                layer.mode('polygon');
                break;
            case TOOLBAR_KEYS.IMPORT:    // import tool
                layer.mode('polygon');
                break;
            default:

                break;

        }
    }, [props.currentTool])

    useEffect(() => {
        console.log("Current annotation changed.");
        const currentState = props.currentAnnotation?.currentState;
        const prevState = props.prevCurrentAnnotation?.currentState;
        const tile_id = currentState?.tile_id;
        const prevTileId = prevState?.tile_id;
        const annotationId = currentState?.id;
        const prevAnnotationId = prevState?.id;

        // If the current annotation is associated with a tile feature, "redraw" the feature.
        if (tile_id) {
            const feature = getTileFeatureById(geojs_map, LAYER_KEYS.GT, tile_id);
            redrawTileFeature(feature, { currentAnnotationId: currentState?.id });

            if (!polygonClicked.current) {  // The polygon was selected from the ground truth list.
                const centroid = currentState.parsedCentroid;

                geojs_map.current.transition({
                    center: { x: centroid.coordinates[0], y: centroid.coordinates[1] },
                    duration: 500,
                    ease: function (t: number) {
                        return 1 - Math.pow(1 - t, 2);
                    }
                })
            }
        }

        // If the previous current annotation is associated with a tile feature, "redraw" the old tile.
        if (prevTileId && prevTileId !== tile_id) {
            const feature = getTileFeatureById(geojs_map, LAYER_KEYS.GT, prevTileId);
            redrawTileFeature(feature);
        }

        // TODO: PUT is called even when the annotation has been deleted. The PUT fails, which is fine, but it's not efficient.
        if (prevAnnotationId && prevAnnotationId !== annotationId && props.currentImage && props.currentClass) {
            putAnnotation(props.currentImage.id, prevState).then(() => {
                console.log("Annotation updated.")
            });
        }

    }, [props.currentAnnotation])

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