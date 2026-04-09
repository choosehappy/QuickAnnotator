import React, { useEffect, useState, useRef, useCallback, act } from 'react';
import geo from "geojs"
import { Annotation, Image, AnnotationClass, Tile, CurrentAnnotation, PutAnnArgs, AnnotationResponse, TileRef, PredFeatureType } from "../types.ts"
import { searchTileRefsByBbox, fetchAllAnnotations, postAnnotations, operateOnAnnotation, putAnnotation, removeAnnotations, getAnnotationsForTileIds, getAnnotationsWithinPolygon, searchTileRefsWithinPolygon, fetchTileBoundingBoxes, fetchImageMetadata, searchTileByCoordinates, predictTiles } from "../helpers/api.ts";
import { Point, Polygon, Feature, Position, GeoJsonGeometryTypes } from "geojson";

import { TOOLBAR_KEYS, INTERACTION_MODE, LAYER_KEYS, TILE_STATUS, MODAL_DATA, RENDER_PREDICTIONS_INTERVAL, RENDER_DELAY, MAP_TRANSLATION_DELAY, MASK_CLASS_ID, COOKIE_NAMES, POLYGON_OPERATIONS, POLYGON_CREATE_STYLE, POLYGON_CREATE_STYLE_SECONDARY, IMPORT_CREATE_STYLE, LASSO_SELECT_STYLE, BRUSH_CREATE_STYLE, BRUSH_CREATE_STYLE_SECONDARY, BRUSH_SIZE, UI_SETTINGS, MAX_ZOOM } from "../helpers/config.tsx";

import { computeFeaturesToRender, getTileFeatureById, redrawTileFeature, createGTTileFeature, createPredTileFeature, createPendingTileFeature, getFeatIdsRendered, tileIdIsValid, getScaledSize, createCirclePolygon, createConnectingRectangle, TileRefStore, getTileFeatureByTileId, removeFeatureById, getTileDownsampleLevel, getPolygonSimplifyTolerance, createTileStatusFeature } from '../utils/map.ts';
import { useCookies } from 'react-cookie';
import { useSearchParams, useNavigate } from "react-router-dom";
import { useHotkeys, isHotkeyPressed } from 'react-hotkeys-hook';
import { useAsyncGuard } from '../utils/useAsyncGuard.ts';


interface Props {
    currentImage: Image | null;
    currentAnnotationClass: AnnotationClass | null;
    currentAnnotation: CurrentAnnotation | null;
    setCurrentAndPreviousAnnotation: (newAnnotation: Annotation | null) => void;
    pushAnnotationStateToUndoStack: (annotation: Annotation) => void;
    prevCurrentAnnotation: React.MutableRefObject<CurrentAnnotation | null>;
    gts: Annotation[];
    setGts: React.Dispatch<React.SetStateAction<Annotation[]>>;
    preds: Annotation[];
    setPreds: React.Dispatch<React.SetStateAction<Annotation[]>>;
    currentTool: string | null;
    setCurrentTool: React.Dispatch<React.SetStateAction<string | null>>;
    selectedPred: CurrentAnnotation | null;
    setSelectedPred: React.Dispatch<React.SetStateAction<CurrentAnnotation | null>>;
    ctrlHeld: boolean;
    setCtrlHeld: React.Dispatch<React.SetStateAction<boolean>>;
    highlightedPreds: Annotation[] | null;
    setHighlightedPreds: React.Dispatch<React.SetStateAction<Annotation[] | null>>;
    multiSelectedAnnotations: Annotation[];
    setMultiSelectedAnnotations: React.Dispatch<React.SetStateAction<Annotation[]>>;
    activeModal: number | null;
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
    setMouseCoords: React.Dispatch<React.SetStateAction<{ x: number, y: number } | null>>;
    gtLayerVisible: boolean;
    predLayerVisible: boolean;
    tileStatusLayerVisible: boolean;
}

const ViewportMap = (props: Props) => {
    const viewRef = useRef(null);
    const geojs_map = useRef<geo.map | null>(null);
    const polygonClicked = useRef<Boolean>(false);  // We need this to ensure polygon clicked and background clicked are mutually exclusive, because geojs does not provide control over event propagation.
    const { startCall, guard } = useAsyncGuard();
    const featureIdsToUpdate = useRef<number[]>([]);
    const [cookies, setCookies] = useCookies([COOKIE_NAMES.SKIP_CONFIRM_IMPORT]);
    const [searchParams, setSearchParams] = useSearchParams();
    const lastBrushState = useRef<{ stateId: number, coords: [Position] } | null>(null);
    const downsampleLevel = useRef<number>(0);

    let zoomPanTimeout: any = null;

    const processGTFeature = async (imageId: number, annotationClassId: number, layer: any, featureId: number, tileIds: number[], gtFeaturesToRender: Set<number>): Promise<Annotation[]> => {
        const shouldRenderFeature = gtFeaturesToRender.has(featureId);
        const shouldUpdateFeature = featureIdsToUpdate.current.includes(featureId);
        let annotations: Annotation[] = [];
        if (shouldRenderFeature || shouldUpdateFeature) {
            const resp = await getAnnotationsForTileIds(imageId, annotationClassId, tileIds, true, getPolygonSimplifyTolerance(geojs_map.current));
            annotations = resp.data.map(annResp => new Annotation(annResp, annotationClassId, featureId));
            const webGLFeature = getTileFeatureById(layer, featureId, PredFeatureType.annotation);
            if (shouldRenderFeature && !webGLFeature) {
                const feature = createGTTileFeature({ featureId: featureId, tileIds: tileIds }, annotations, layer, props.currentAnnotationClass, props.currentAnnotation?.currentState?.id);
                feature.geoOn(geo.event.feature.mousedown, handleMousedownOnPolygon);
            } else {
                redrawTileFeature(webGLFeature, {}, annotations);
            }
        } else {
            const webGLFeature = getTileFeatureById(layer, featureId, PredFeatureType.annotation);
            annotations = webGLFeature.data();
        }
        return annotations;
    }

    const processPredFeature = async (imageId: number, annotationClassId: number, layer: any, featureId: number, tileIds: number[]): Promise<Annotation[]> => {
        const annsResp = await getAnnotationsForTileIds(imageId, annotationClassId, tileIds, false, getPolygonSimplifyTolerance(geojs_map.current));
        const annotations = annsResp.data.map(annResp => new Annotation(annResp, annotationClassId, featureId));

        const existingFeature = getTileFeatureById(layer, featureId, PredFeatureType.annotation);

        if (existingFeature) {
            redrawTileFeature(existingFeature, { featureId: featureId, tileIds: tileIds}, annotations);
        } else {
            const feature = createPredTileFeature({ featureId: featureId, tileIds: tileIds }, annotations, layer, props.currentAnnotationClass);
        }

        return annotations;
    }

    const computeTileStatusFeature = async (imageId: number, annotationClassId: number, layer: any, featureId: number, tileIds: number[]) => {
        // Get tile statuses using the predictTiles API method
        const tileResp = await predictTiles(imageId, annotationClassId, tileIds, true);
        if (tileResp.status !== 200) {
            console.error(`Error predicting tiles for feature ${featureId}`);
        }

        // Check for existing feature
        const existingFeature = getTileFeatureById(layer, featureId, PredFeatureType.annotation);
        if (existingFeature) {
            redrawTileFeature(existingFeature, { featureId: featureId, tileIds: tileIds}, tileResp.data);
        } else {
            createTileStatusFeature({ featureId: featureId, tileIds: tileIds }, tileResp.data, layer);
        }

        // Create a feature in the layer displaying the tile statuses with of all tiles
        return false;
    }

    const viewportClear = (clearGts: boolean, clearPreds: boolean, clearTileStatus: boolean) => {
        if (geojs_map.current) {
            const layers = geojs_map.current.layers();
            if (clearGts) {
                layers[LAYER_KEYS.GT].clear();
            }
            if (clearPreds) {
                layers[LAYER_KEYS.PRED].clear();
            }
            if (clearTileStatus) {
                layers[LAYER_KEYS.TILE_STATUS].clear();
            }
        }
    }

    const viewportRender = async (renderGts: boolean, renderPreds: boolean, renderTileStatus: boolean, imageId: number, annotationClassId: number) => {
        const callToken = startCall();
        const withGuard = guard(callToken);
        // Safeguards against invalid application state.
        if (!props.currentImage) {
            console.error("Error: currentImage is not defined.");
            return;
        }
        if (!props.currentAnnotationClass) {
            console.error("Error: currentAnnotationClass is not defined.");
            return;
        }
        if (!geojs_map.current) {
            console.error("Error: geojs_map is not initialized.");
            return;
        }

        // Get map bounds
        const bounds = geojs_map.current.bounds();
        const x1 = bounds.left;
        const y1 = Math.abs(bounds.top);
        const x2 = bounds.right;
        const y2 = Math.abs(bounds.bottom);
        const newDownsampleLevel = getTileDownsampleLevel(geojs_map.current);
        const layers = geojs_map.current.layers()

        // Get all tile features within bounds
        const resp = await withGuard(() => searchTileRefsByBbox(imageId, annotationClassId, x1, y1, x2, y2, false, newDownsampleLevel));
        if (!resp) {
            return;
        }
        const tileRefs: TileRef[] = resp.data;
        const tileRefStore = new TileRefStore(tileRefs);

        // Prepare annotation lists
        // NOTE: Pontential race condition here - mutable lists being updated in parallel async calls.
        let gtAnns: Annotation[] = [];
        let predAnns: Annotation[] = [];

        // Remove off-screen features only for layers that are being re-rendered
        const layersToUpdate = [
            ...(renderGts ? [LAYER_KEYS.GT] : []),
            ...(renderPreds ? [LAYER_KEYS.PRED] : []),
            ...(renderTileStatus ? [LAYER_KEYS.TILE_STATUS] : []),
        ];
        layersToUpdate.forEach(layerKey => {
            const layer = layers[layerKey];
            const featuresRendered = getFeatIdsRendered(layer, PredFeatureType.annotation);
            const { featuresToRemove } = computeFeaturesToRender(featuresRendered, tileRefStore.getAllGroupIds());
            featuresToRemove.forEach((featureId) => removeFeatureById(layer, featureId, PredFeatureType.annotation));
        });

        // Get features to render for Ground Truth
        const gtLayer = layers[LAYER_KEYS.GT];
        const gtFeaturesRendered = getFeatIdsRendered(gtLayer, PredFeatureType.annotation);
        const { featuresToRender: gtFeaturesToRender } = computeFeaturesToRender(gtFeaturesRendered, tileRefStore.getAllGroupIds());

        // Should any layers be cleared due to downsample level change?
        if (downsampleLevel.current !== newDownsampleLevel) {
            downsampleLevel.current = newDownsampleLevel;
            viewportClear(renderGts, renderPreds, renderTileStatus);
        }
        // Process each group in parallel
        await Promise.all(Array.from(tileRefStore).map(async (group) => {
            // Get info about the current group
            const featureId = group[0];
            const tileRefs = group[1];
            const tileIds = tileRefs.map(tr => tr.tile_id);

            if (renderGts) {
                const newGts = await withGuard(() => processGTFeature(imageId, annotationClassId, gtLayer, featureId, tileIds, gtFeaturesToRender));
                if (newGts) {
                    gtAnns = gtAnns.concat(newGts);
                    props.setGts(gtAnns);
                }
            }

            const shouldRequestPredictions = (renderTileStatus || renderPreds) && annotationClassId !== MASK_CLASS_ID;

            // Tile Status
            if (shouldRequestPredictions) {
                if (renderTileStatus) {
                    await withGuard(() => computeTileStatusFeature(imageId, annotationClassId, layers[LAYER_KEYS.TILE_STATUS], featureId, tileIds));
                } else {
                    // Otherwise, just call predictTiles without returning anything
                    await withGuard(() => predictTiles(imageId, annotationClassId, tileIds, false));
                }

                if (renderPreds) {
                    const newPreds = await withGuard(() => processPredFeature(imageId, annotationClassId, layers[LAYER_KEYS.PRED], featureId, tileIds));
                    if (newPreds) {
                        predAnns = predAnns.concat(newPreds);
                        props.setPreds(predAnns);
                    }
                }
            }
        }));
    }


    function handleMousedownOnPolygon(evt) {
        console.log("Polygon clicked.")
        console.log(evt.data)
        polygonClicked.current = true;

        const clickedAnnotation: Annotation = evt.data;

        // Ctrl+click: toggle annotation in multi-selection
        if (isHotkeyPressed('ctrl') && props.currentTool === TOOLBAR_KEYS.POINTER) {
            props.setMultiSelectedAnnotations((prev: Annotation[]) => {
                const exists = prev.some(a => a.id === clickedAnnotation.id);
                if (exists) {
                    return prev.filter(a => a.id !== clickedAnnotation.id);
                } else {
                    return [...prev, clickedAnnotation];
                }
            });
        } else {
            // Note: gets called even when clicking on an already selected polygon.
            props.setCurrentAndPreviousAnnotation(clickedAnnotation);
        }

        setTimeout(() => {
            polygonClicked.current = false;
        }, 0);
    }

    const handleMousedown = (evt) => {
        const annotationLayer = geojs_map.current.layers()[LAYER_KEYS.ANN];
        const mode = annotationLayer.mode();
        console.log(`Mouse down detected. Mode: ${mode}`);


        if (!polygonClicked.current && !isHotkeyPressed('ctrl') && props.currentAnnotation) {
            const currentState = props.currentAnnotation.currentState;
            const featureId = currentState?.featureId;
            if (tileIdIsValid(featureId)) {
                props.setCurrentAndPreviousAnnotation(null);
            }
        }

        // Clear multi-selection when clicking empty space (without Ctrl held)
        if (!polygonClicked.current && !isHotkeyPressed('ctrl') && props.multiSelectedAnnotations.length > 0) {
            props.setMultiSelectedAnnotations([]);
        }

        // Start lasso selection when Ctrl+clicking on empty space in pointer mode.
        // If a polygon was clicked, handleMousedownOnPolygon already handled the
        // Ctrl+click toggle, so we skip lasso entry.
        if (!polygonClicked.current && isHotkeyPressed('ctrl') && props.currentTool === TOOLBAR_KEYS.POINTER) {
            const annotationLayer = geojs_map.current.layers()[LAYER_KEYS.ANN];
            annotationLayer.mode('polygon', undefined, {
                createStyle: LASSO_SELECT_STYLE
            });
        }
    }

    const handleBrushAction = (evt) => {
        const map = geojs_map.current;
        const layers = map.layers();
        const brushLayer = layers[LAYER_KEYS.BRUSH];
        const annotationLayer = layers[LAYER_KEYS.ANN];
        const lastState = lastBrushState.current;
        const scaledSize = getScaledSize(map, BRUSH_SIZE); // Get the scaled size based on the current zoom level

        if (evt.evt.event === geo.event.actionup) {
            handleNewAnnotation(evt);
            return; // Brush action ends on mouse up.
        }
        const brushPixelTolerance = 0.05; // Determines the side length of the brush polygon.
        if (evt.event === geo.event.annotation.cursor_action) {
            if (evt.operation && evt.operation !== 'union' && evt.operation !== 'difference') {
                return;
            }
            const coords1 = brushLayer.annotations()[0]._coordinates();
            const c1x = coords1[0].x;
            const c1y = coords1[0].y;
            const source = createCirclePolygon(c1x, c1y, scaledSize, annotationLayer, brushPixelTolerance); // Create a polygon for the brush action

            if (lastState && lastState.stateId && lastState.stateId === evt.evt.state.stateId) {
                const coords2 = lastState.coords; // Store the previous point coordinates  
                const c2x = coords2[0].x;
                const c2y = coords2[0].y;

                if (c1x !== c2x || c1y !== c2y) {
                    source.push(createConnectingRectangle(c1x, c1y, c2x, c2y, scaledSize)); // Create a rectangle connecting the previous and current points
                }
            }
            lastBrushState.current = evt.evt.state;
            lastBrushState.current.coords = coords1;
            geo.util.polyops['union'](annotationLayer, source, { correspond: {}, keepAnnotations: 'exact', style: annotationLayer });
        } else {
            lastBrushState.current = null;
        }
    }


    function handleDeleteAnnotation(evt) {
        console.log("Delete annotation detected.")

        const multiSelected = props.multiSelectedAnnotations;

        // Multi-delete: delete all multi-selected annotations (and currentAnnotation if set)
        if (multiSelected.length > 0) {
            const idsToDelete = new Set(multiSelected.map(a => a.id));
            if (props.currentAnnotation?.currentState) {
                idsToDelete.add(props.currentAnnotation.currentState.id);
            }

            const idsArray = Array.from(idsToDelete);
            if (!props.currentImage || !props.currentAnnotationClass) return;

            removeAnnotations(props.currentImage.id, props.currentAnnotationClass.id, idsArray, true).then(() => {
                props.setMultiSelectedAnnotations([]);
                props.setCurrentAndPreviousAnnotation(null);
                viewportClear(true, false, false);
                viewportRender(true, false, false, props.currentImage.id, props.currentAnnotationClass.id);
                console.log(`Deleted ${idsArray.length} annotations.`);
            });
            return;
        }

        // Single delete: existing behavior
        if (!props.currentAnnotation) return;    // Delete operation only allowed if an annotation is selected.

        const currentState: Annotation | undefined = props.currentAnnotation.currentState;
        if (!currentState) {
            console.log("No current annotation state found.");
            return;
        }
        const featureId = currentState.featureId;

        const annotationId = currentState.id;

        const layer = geojs_map.current.layers()[LAYER_KEYS.GT];

        if (annotationId && props.currentImage && props.currentAnnotationClass && tileIdIsValid(featureId)) {
            removeAnnotations(props.currentImage.id, props.currentAnnotationClass.id, [annotationId], true).then(() => {
                const feature = getTileFeatureById(layer, featureId, PredFeatureType.annotation);
                const data = feature.data();
                const deletedData = data.filter((d: Annotation) => d.id !== annotationId);

                const updatedGroundTruths = props.gts.filter((gt: Annotation) => gt.id !== annotationId);
                props.setGts(updatedGroundTruths);
                redrawTileFeature(feature, {}, deletedData);
                props.setCurrentAndPreviousAnnotation(null);
                console.log(`Annotation id=${annotationId} deleted.`)
            })
        }
    }


    const updateAnnotation = (currentState: Annotation, newPolygon: Polygon, operation: POLYGON_OPERATIONS) => {
        const layer = geojs_map.current.layers()[LAYER_KEYS.GT];
        const featureId = currentState.featureId;
        if (!tileIdIsValid(featureId)) return;
        const feature = getTileFeatureById(layer, featureId, PredFeatureType.annotation);
        const data = feature.data();
        operateOnAnnotation(currentState, newPolygon, operation).then((resp) => {
            const newState = new Annotation(resp.data, currentState.annotation_class_id, currentState.featureId);
            if (resp.data.polygon === null) {
                // Remove the annotation from updated data and ground truths
                const updatedData: Annotation[] = data.filter((d: Annotation) => d.id !== currentState.id);
                const updatedGroundTruths = props.gts.filter((gt: Annotation) => gt.id !== currentState.id);

                props.setGts(updatedGroundTruths);
                redrawTileFeature(feature, {}, updatedData);

                // Call the deleteAnnotation API method
                if (props.currentImage && props.currentAnnotationClass && currentState.id) {
                    removeAnnotations(props.currentImage.id, props.currentAnnotationClass.id, [currentState.id], true)
                        .then(() => {
                            console.log(`Annotation id=${currentState.id} deleted due to null polygon.`);
                        });
                }
                props.setCurrentAndPreviousAnnotation(null);
            } else {
                // Update the annotation
                const updatedData: Annotation[] = data.map((d: Annotation) => d.id === currentState.id ? newState : d);
                const updatedGroundTruths = props.gts.map((gt: Annotation) => gt.id === currentState.id ? newState : gt);

                props.setGts(updatedGroundTruths);
                redrawTileFeature(feature, { currentAnnotationId: currentState.id }, updatedData);
                props.pushAnnotationStateToUndoStack(newState);
            }
        });
    }

    const addAnnotation = (newPolygon: Polygon) => {
        const currentImage: Image | null = props.currentImage;
        const currentAnnotationClass: AnnotationClass | null = props.currentAnnotationClass;
        if (!currentImage || !currentAnnotationClass) {
            console.error("Error: currentImage or currentAnnotationClass is not defined.");
            return;
        }

        postAnnotations(currentImage.id, currentAnnotationClass.id, [newPolygon]).then(async (resp) => {
            if (resp.status === 200) {
                const centroid = newPolygon.coordinates[0][0]; // Directly access the coordinates
                const tileResp = await searchTileByCoordinates(currentImage.id, currentAnnotationClass.id, centroid[0], centroid[1], downsampleLevel.current);
                const featureId = tileResp.data.downsampled_tile_id;
                if (featureId === null || !tileIdIsValid(featureId)) return;
                const annotation = new Annotation(resp.data[0], currentAnnotationClass.id, featureId);
                const tileId = annotation.tile_id;
                if (tileId === null || !tileIdIsValid(tileId)) return;
                const layer = geojs_map.current.layers()[LAYER_KEYS.GT];
                let feature = getTileFeatureById(layer, featureId, PredFeatureType.annotation);
                if (feature) {  // Feature already exists, just update its data.
                    const data = feature.data();
                    const updatedData = data.concat(annotation);
                    redrawTileFeature(feature, {}, updatedData);
                } else {    // Create a new feature for the tile.
                    feature = createGTTileFeature({ featureId: featureId, tileIds: [tileId] }, [annotation], layer, currentAnnotationClass);
                    feature.geoOn(geo.event.feature.mousedown, handleMousedownOnPolygon);
                }
                props.setGts((prev: Annotation[]) => prev.concat(annotation));
            } else if (resp.status === 400) {
                alert("The annotation could not be saved as it is outside the tissue mask. Please try again.");
            }
        });
    }


    const getPolygonFromAnnotationLayer = (): Polygon | null => {
        const annotationLayer = geojs_map.current.layers()[LAYER_KEYS.ANN];
        const annotations = annotationLayer.annotations();
        if (annotations && annotations.length > 0) {
            const geometry = annotations[0].geojson().geometry
            if (geometry.type === "Polygon") {
                return geometry as Polygon;
            }
            if (geometry.type === "Point") {
                const coords = geometry.coordinates;
                const polygon: Polygon = {
                    type: "Polygon",
                    coordinates: [[
                        [coords[0], coords[1] + 0.0001],
                        [coords[0] - 0.0001, coords[1] - 0.0001],
                        [coords[0] + 0.0001, coords[1] - 0.0001],
                        [coords[0], coords[1] + 0.0001] // Closing the triangle
                    ]],
                };
                return polygon;
            }
        }
        return null;
    }

    const handleNewAnnotation = async (evt) => {
        console.log("New annotation detected.")
        const annotationLayer = geojs_map.current.layers()[LAYER_KEYS.ANN];
        const { currentImage, currentAnnotationClass, currentAnnotation, currentTool, setHighlightedPreds, setActiveModal } = props;

        if (!currentImage || !currentAnnotationClass || !currentTool) {
            console.error("Error: currentImage, currentAnnotationClass or currentTool is not defined.");
            return;
        }

        // Get the polygon from the annotation layer.
        const polygon = getPolygonFromAnnotationLayer();
        if (!polygon) {
            console.log("No polygon found in the annotation layer while changing annotation mode .");
            return;
        }

        // Clear the annotation layer
        annotationLayer.removeAllAnnotations();
        console.log("Annotation layer cleared.");


        if (currentTool === TOOLBAR_KEYS.POLYGON || currentTool === TOOLBAR_KEYS.BRUSH) {
            const currentState = currentAnnotation?.currentState;
            const hotKeyPressed = isHotkeyPressed('ctrl');

            // If currentAnnotation exists, update the currentAnnotation
            if (currentState) {
                console.log("Current annotation exists. Updating...")
                updateAnnotation(currentState, polygon, hotKeyPressed ? POLYGON_OPERATIONS.DIFFERENCE : POLYGON_OPERATIONS.UNION);

            } else {    // If currentAnnotation does not exist, create a new annotation in the database.
                console.log("Current annotation does not exist. Creating...")
                if (!hotKeyPressed) {
                    addAnnotation(polygon);
                }
            }
        } else if (currentTool === TOOLBAR_KEYS.IMPORT) {
            const resp = await getAnnotationsWithinPolygon(currentImage.id, currentAnnotationClass.id, false, polygon); // We don't want to simplify imported annotations
            if (resp.status === 200) {
                // In this case we set the annotation's featureId to null since we don't need to redraw specific tiles.
                const anns = resp.data.map((annResp: AnnotationResponse) => new Annotation(annResp, currentAnnotationClass.id, null));
                if (anns.length > 0) {
                    const featureIds = getFeatIdsRendered(geojs_map.current.layers()[LAYER_KEYS.GT], PredFeatureType.annotation);
                    featureIdsToUpdate.current = featureIds;
                    redrawHighlightedPreds(anns);
                    if (cookies[COOKIE_NAMES.SKIP_CONFIRM_IMPORT]) {
                        postAnnotations(currentImage.id, currentAnnotationClass?.id, anns.map(ann => ann.parsedPolygon)).then(() => {
                            redrawHighlightedPreds([]);  // Clear the redrawing of highlighted predictions by passing an empty array.
                            viewportRender(true, false, false, currentImage.id, currentAnnotationClass.id).then(() => {   
                                console.log("Viewport render complete after import.");
                            });
                        });
                    } else {
                        // Open the import confirmation modal
                        setActiveModal(MODAL_DATA.IMPORT_CONF.id);
                    }
                } else {
                    alert("No annotations found within the lasso. Please try again.");
                }
                annotationLayer.mode('point');
                // }
            }
        } else if (currentTool === TOOLBAR_KEYS.POINTER) {
            // Lasso selection of GT annotations
            const resp = await getAnnotationsWithinPolygon(currentImage.id, currentAnnotationClass.id, true, polygon);
            if (resp.status === 200) {
                const anns = resp.data.map((annResp: AnnotationResponse) => new Annotation(annResp, currentAnnotationClass.id, null));
                props.setMultiSelectedAnnotations((prev: Annotation[]) => {
                    const existingIds = new Set(prev.map(a => a.id));
                    const newAnns = anns.filter((a: Annotation) => !existingIds.has(a.id));
                    return [...prev, ...newAnns];
                });
                if (anns.length === 0) {
                    console.log("No ground truth annotations found within the lasso.");
                } else {
                    console.log(`Selected ${anns.length} ground truth annotations via lasso.`);
                }
            }
            annotationLayer.mode(null);  // Return to pan mode
        }
    }


    const handleAnnotationModeChange = (evt) => {
        console.log(`Mode changed from ${evt.oldMode} to ${evt.mode}`);
        const layer = geojs_map.current?.layers()[LAYER_KEYS.ANN];
        if (evt.mode === null) {    // Annotation creation events and ctrl key events automatically set annotationLayer mode to null
            switch (props.currentTool) {
                case TOOLBAR_KEYS.POLYGON:
                    activatePolygonTool(layer, props.ctrlHeld);
                    break;
                case TOOLBAR_KEYS.IMPORT:
                    activateImportTool(layer, props.ctrlHeld);
                    break;
                case TOOLBAR_KEYS.POINTER:
                    // After lasso selection completes, return to pan mode
                    activatePointerTool(layer);
                    break;
                case TOOLBAR_KEYS.BRUSH:
                    // activateBrushTool(layer, props.ctrlHeld);
                    break;
                default:
                    break;
            }
        }
    }

    const handleZoomPan = () => {
        console.log('Zooming or Panning...');

        // Clear the previous timeout if the zoom continues
        if (zoomPanTimeout) clearTimeout(zoomPanTimeout);
        // Set a new timeout to detect when zooming has stopped
        zoomPanTimeout = setTimeout(() => {
            console.log('Zooming or Panning stopped.');
            setBoundsQuery();
            viewportRender(props.gtLayerVisible, props.predLayerVisible, props.tileStatusLayerVisible, props.currentImage.id, props.currentAnnotationClass.id).then(() => {   // TODO: rename active variable
                console.log("Viewport render complete.");
            });
        }, RENDER_DELAY); // Adjust this timeout duration as needed
    };

    const translateMap = (x: number, y: number) => {
        geojs_map.current.transition({
            center: { x: x, y: y },
            duration: MAP_TRANSLATION_DELAY,
            ease: function (t: number) {
                return 1 - Math.pow(1 - t, 2);
            }
        })
    }

    /**
     * Set the view (image bounds) of the current image as a
     * query string parameter.
     */
    const setBoundsQuery = () => {
        var bounds, left, right, top, bottom, rotation;
        const map = geojs_map.current;
        if (map && props.currentImage) {
            bounds = map.bounds();
            rotation = (map.rotation() * 180 / Math.PI).toFixed();
            left = bounds.left.toFixed();
            right = bounds.right.toFixed();
            top = bounds.top.toFixed();
            bottom = bounds.bottom.toFixed();
            setSearchParams({
                bounds: [
                    left, top, right, bottom, rotation
                ].join(','),
            }, { replace: true });
        }
    }

    /**
     * Get the view from the query string and set it on the image.
     */
    const setImageBounds = () => {
        const boundsstring = searchParams.get('bounds');
        const map = geojs_map.current;
        if (!boundsstring || !map) {
            return;
        }
        const bounds = boundsstring.split(',');
        map.bounds({
            left: parseFloat(bounds[0]),
            top: parseFloat(bounds[1]),
            right: parseFloat(bounds[2]),
            bottom: parseFloat(bounds[3])
        });
        var rotation = parseFloat(bounds[4]) || 0;
        map.rotation(rotation * Math.PI / 180);
    }

    const initializeMap = () => {
        const img = props.currentImage;

        if (!img) { console.error("No image provided for map initialization."); return; }
        if (!viewRef.current) { console.error("View reference is not set."); return; }

        const params = geo.util.pixelCoordinateParams(
            viewRef.current, img.base_width, img.base_height, img.dz_tilesize, img.dz_tilesize);

        const map = geo.map({ ...params.map, max: MAX_ZOOM });
        const interactor = map.interactor();

        // Disable hotkeys for zooming to prevent conflicts with annotation tools
        const keyboardOptions = interactor.keyboard();
        keyboardOptions.actions['zoom.0'] = [];
        keyboardOptions.actions['zoom.3'] = [];
        keyboardOptions.actions['zoom.6'] = [];
        keyboardOptions.actions['zoom.9'] = [];
        keyboardOptions.actions['zoom.12'] = [];
        keyboardOptions.actions['zoom.15'] = [];
        keyboardOptions.actions['zoom.18'] = [];
        interactor.keyboard(keyboardOptions);

        // Disable rotation interactions
        interactor.removeAction(geo.geo_action.rotate, 'button rotate');
        interactor.removeAction(geo.geo_action.rotate, 'wheel rotate');

        params.layer.url = `/api/v1/image/${img.id}/patch_file/{z}/{x}_{y}.png`;
        console.log("OSM layer loaded.");

        const groundTruthLayer = map.createLayer('feature', { features: ['polygon'], renderer: 'webgl' });
        const predictionsLayer = map.createLayer('feature', { features: ['polygon'], renderer: 'webgl' });
        const tileStatusLayer = map.createLayer('feature', { features: ['quad'], renderer: 'webgl' })

        map.createLayer('osm', { ...params.layer, zIndex: 0 })

        const annotationLayer = map.createLayer('annotation',
            {
                active: true,
                zIndex: 2,
                finalPointProximity: UI_SETTINGS.finalPointProximity,
                continuousCloseProximity: UI_SETTINGS.continuousCloseProximity,
                showLabels: false,
            });

        const brushLayer = map.createLayer('annotation', {
            showLabels: false
        });

        const uiLayer = map.createLayer('ui');

        // Fetch image metadata and set scale
        try {
            fetchImageMetadata(img.id).then((metadataResp) => {
                const mpp = metadataResp.data.mpp; // microns per pixel
                const micronUnits = [
                    { unit: 'µm', scale: 1 }, // for single micron
                    { unit: 'mm', scale: 1000 }, // for millimeters
                    { unit: 'cm', scale: 10000 }, // for centimeters
                ];
                uiLayer.createWidget('scale', {
                    position: { left: 10, bottom: 10 },
                    units: micronUnits,
                    scale: mpp,
                });
            }).catch((error) => {
                console.error("Failed to fetch image metadata:", error);
            });
        } catch (error) {
            console.error("Failed to fetch image metadata:", error);
        }
        geojs_map.current = map;
        setImageBounds();
        return null;
    }

    // Register event handlers
    useEffect(() => {
        if (!geojs_map.current) {
            console.error("GeoJS map is not initialized.");
            return;
        }

        const annotationLayer = geojs_map.current.layers()[LAYER_KEYS.ANN];
        if (!annotationLayer) {
            console.error("Annotation layer not found.");
            return;
        }
        const map = geojs_map.current;

        annotationLayer.geoOn(geo.event.mousedown, handleMousedown);
        annotationLayer.geoOn(geo.event.annotation.state, handleNewAnnotation);
        annotationLayer.geoOn(geo.event.annotation.mode, handleAnnotationModeChange);

        const brushLayer = geojs_map.current.layers()[LAYER_KEYS.BRUSH];
        brushLayer.geoOn(geo.event.annotation.cursor_click, handleBrushAction);
        brushLayer.geoOn(geo.event.annotation.cursor_action, handleBrushAction);

        map.geoOn(geo.event.mousemove, function (evt: any) {
            props.setMouseCoords({ x: Math.round(evt.geo.x * 100) / 100, y: Math.round(evt.geo.y * 100) / 100 });
        });
        map.geoOn(geo.event.zoom, handleZoomPan);
        map.geoOn(geo.event.pan, handleZoomPan);
        map.geoOn(geo.event.transition, handleZoomPan);

        return () => {
            // Cleanup event handlers on unmount
            annotationLayer.geoOff(geo.event.mousedown, handleMousedown);
            annotationLayer.geoOff(geo.event.annotation.state, handleNewAnnotation);
            annotationLayer.geoOff(geo.event.annotation.mode, handleAnnotationModeChange);

            brushLayer.geoOff(geo.event.annotation.cursor_click, handleBrushAction);
            brushLayer.geoOff(geo.event.annotation.cursor_action, handleBrushAction);

            window.onkeydown = null;
            map.geoOff(geo.event.mousemove);
            map.geoOff(geo.event.zoom);
            map.geoOff(geo.event.pan);
            map.geoOff(geo.event.transition);
        };
    }, [props.currentImage, props.currentAnnotationClass, props.currentTool, props.currentAnnotation, props.gts, props.ctrlHeld, props.multiSelectedAnnotations]);

    // When the currentAnnotationClass changes
    useEffect(() => {
        if (!props.currentImage || !props.currentAnnotationClass) {
            console.error("Error: currentImage or currentAnnotationClass is not defined.");
            return;
        }

        geojs_map.current?.exit();
        initializeMap()

        const currentAnnotationClassId = props.currentAnnotationClass?.id;
        if (!currentAnnotationClassId) return;

        // // Clear all existing annotations.
        props.setGts([]);
        props.setPreds([]);
        props.setMultiSelectedAnnotations([]);

        viewportRender(props.gtLayerVisible, props.predLayerVisible, props.tileStatusLayerVisible, props.currentImage.id, props.currentAnnotationClass.id).then(() => {
            console.log("Viewport render on annotation class change complete.");
        });

    }, [props.currentAnnotationClass]); // May need to add layer visisblity states here


    // Individual tool activation methods
    function activatePointerTool(layer: any) {
        console.log("toolbar is 0");
        layer?.mode(null);
    }

    function activatePolygonTool(layer: any, secondary: boolean) {
        layer.mode('polygon', undefined, {
            createStyle: secondary ? POLYGON_CREATE_STYLE_SECONDARY : POLYGON_CREATE_STYLE
        });
    }

    function activateImportTool(layer: any, secondary: boolean) {
        layer.mode(secondary ? 'polygon' : 'point', undefined, {
            createStyle: secondary ? IMPORT_CREATE_STYLE : {}
        });
    }

    function activateBrushTool(layer: any, secondary: boolean) {
        if (!geojs_map.current) {
            console.error("GeoJS map is not initialized.");
            return;
        }
        const layers = geojs_map.current.layers();
        const brushLayer = layers[LAYER_KEYS.BRUSH];

        if (!brushLayer) {
            console.error("Brush layer not found.");
            return;
        }

        brushLayer.mode(null);
        brushLayer.removeAllAnnotations();


        var centerX = 0;  // your desired center X  
        var centerY = 0;  // your desired center Y  

        var pointAnnotation = geo.annotation.pointAnnotation({
            position: { x: centerX, y: centerY }, // your desired center position  
            style: secondary ? BRUSH_CREATE_STYLE_SECONDARY : BRUSH_CREATE_STYLE,
        });
        brushLayer.addAnnotation(pointAnnotation);

        brushLayer.mode(brushLayer.modes.cursor, pointAnnotation);
        geojs_map.current.draw();

        lastBrushState.current = null;
    }

    function removeCursor() {
        if (!geojs_map.current) {
            console.error("GeoJS map is not initialized.");
            return;
        }
        const layers = geojs_map.current.layers();
        const annotationLayer = layers[LAYER_KEYS.ANN];
        const brushLayer = layers[LAYER_KEYS.BRUSH];

        if (brushLayer) {
            brushLayer.mode(null);
            brushLayer.removeAllAnnotations();
        }

        if (annotationLayer) {
            annotationLayer.mode(null);
        }
    }

    // Update the active tool when the toolbar changes or when the ctrl key is pressed/released.
    useEffect(() => {
        console.log('detected toolbar change');
        const layer = geojs_map.current?.layers()[LAYER_KEYS.ANN];
        if (!layer) return;

        // Clear multi-selection when switching tools
        props.setMultiSelectedAnnotations([]);

        // We need to clean up the cursor
        removeCursor();

        switch (props.currentTool) {
            case null:
                console.log("toolbar is null");
                break;
            case TOOLBAR_KEYS.POINTER:
                activatePointerTool(layer);
                break;
            case TOOLBAR_KEYS.POLYGON:
                activatePolygonTool(layer, false);
                break;
            case TOOLBAR_KEYS.IMPORT:
                activateImportTool(layer, false);
                break;
            case TOOLBAR_KEYS.BRUSH:
                activateBrushTool(layer, false);
                break;
            default:
                break;
        }
    }, [props.currentTool]);


    useEffect(() => {
        console.log("Current annotation changed.");
        const currentState = props.currentAnnotation?.currentState;
        const prevState = props.prevCurrentAnnotation?.current?.currentState;
        const changesMade = props.prevCurrentAnnotation?.current?.hasChanges();
        const featureId = currentState?.featureId;
        const prevFeatureId = prevState?.featureId;
        const annotationId = currentState?.id;
        const prevAnnotationId = prevState?.id;
        const layer = geojs_map.current?.layers()[LAYER_KEYS.GT];
        // If the current annotation is associated with a tile feature, "redraw" the feature.
        if (tileIdIsValid(featureId)) {
            const feature = getTileFeatureById(layer, featureId, PredFeatureType.annotation);
            const multiSelectedIds = props.multiSelectedAnnotations.map(a => a.id);
            redrawTileFeature(feature, { currentAnnotationId: currentState?.id, multiSelectedIds });
            const undoStackLength = props.currentAnnotation?.undoStack.length;

            if (currentState && !polygonClicked.current && undoStackLength && undoStackLength === 1) {  // If the annotation was changed programmatically (not clicked), we center the map.
                const centroid = currentState.parsedCentroid;
                translateMap(centroid.coordinates[0], centroid.coordinates[1]);
            }
        }

        // If the previous current annotation is associated with a tile feature, "redraw" the old tile.
        if (tileIdIsValid(prevFeatureId) && prevFeatureId !== featureId) {
            const feature = getTileFeatureById(layer, prevFeatureId, PredFeatureType.annotation);
            redrawTileFeature(feature);
        }

        // TODO: PUT is called even when the annotation has been deleted. The PUT fails, which is fine, but it's not efficient.
        if (prevAnnotationId && prevAnnotationId !== annotationId && changesMade && props.currentImage && props.currentAnnotationClass) {
            putAnnotation(props.currentImage.id, props.currentAnnotationClass.id, prevState).then(() => {
                console.log("Annotation updated.")
            });
        }

    }, [props.currentAnnotation])

    // Redraw GT features when multi-selection changes
    useEffect(() => {
        const gtLayer = geojs_map.current?.layers()[LAYER_KEYS.GT];
        if (!gtLayer) return;

        const multiSelectedIds = props.multiSelectedAnnotations.map(a => a.id);
        const currentAnnotationId = props.currentAnnotation?.currentState?.id ?? null;

        const features = gtLayer.features().filter((f: any) => f.featureType === 'polygon' && f.props?.type === PredFeatureType.annotation);
        features.forEach((feature: any) => {
            redrawTileFeature(feature, { currentAnnotationId, multiSelectedIds });
        });
    }, [props.multiSelectedAnnotations])

    useEffect(() => {
        const x = props.selectedPred?.currentState?.parsedCentroid?.coordinates[0];
        const y = props.selectedPred?.currentState?.parsedCentroid?.coordinates[1];
        if (x && y) translateMap(x, y);
    }, [props.selectedPred]);

    // When the highlighted predictions change, redraw the features
    function redrawHighlightedPreds(highlightedPreds: Annotation[]) {
        if (!geojs_map.current || !props.currentImage || !props.currentAnnotationClass) return;

        const predLayer = geojs_map.current.layers()[LAYER_KEYS.PRED];
        if (!predLayer) return;
        const features = predLayer.features().filter((f: any) => f.featureType === 'polygon');
        // const featuresToRedraw = features.filter((f: any) => featIdsToUpdate.includes(f.props.featureId));
        const highlightedPolyIds = highlightedPreds.map(ann => ann.id);

        features.forEach((f: any) => {
            redrawTileFeature(f, highlightedPolyIds ? { highlightedPolyIds: highlightedPolyIds } : {});
        });
        console.log("Redrew highlighted predictions.");
    }


    useHotkeys('backspace, delete', handleDeleteAnnotation, [props.currentAnnotation, props.currentImage, props.currentAnnotationClass, props.gts, props.multiSelectedAnnotations]);
    useHotkeys('ctrl', (event) => {
        const isKeyDown = event.type === 'keydown';
        props.setCtrlHeld(isKeyDown);
        console.log(`Ctrl key ${isKeyDown ? 'down' : 'up'}.`);
        const annotationLayer = geojs_map.current?.layers()[LAYER_KEYS.ANN];
        const brushLayer = geojs_map.current?.layers()[LAYER_KEYS.BRUSH];
        if (!annotationLayer) return;

        switch (props.currentTool) {
            case TOOLBAR_KEYS.POINTER:
                if (!isKeyDown) {
                    annotationLayer.mode(null);
                }
                // When Ctrl is pressed, don't enter polygon mode immediately.
                // handleMousedown will enter lasso polygon mode only when
                // clicking on empty space, allowing clicks on annotations
                // to pass through to handleMousedownOnPolygon for toggle.
                break;
            case TOOLBAR_KEYS.POLYGON:
                annotationLayer.annotations()[0]?.createStyle(isKeyDown ? POLYGON_CREATE_STYLE_SECONDARY : POLYGON_CREATE_STYLE);
                break;
            case TOOLBAR_KEYS.BRUSH:
                brushLayer.annotations()[0]?.createStyle(isKeyDown ? BRUSH_CREATE_STYLE_SECONDARY : BRUSH_CREATE_STYLE);
                break;
            case TOOLBAR_KEYS.IMPORT:
                annotationLayer.mode(isKeyDown ? 'polygon' : 'point', undefined, {
                    createStyle: isKeyDown ? IMPORT_CREATE_STYLE : {}
                });
                break;
            default:
                break;
        }
    }, { keydown: true, keyup: true }, [props.currentTool]);

    useEffect(() => {
        if (!geojs_map.current) return;

        const layers = geojs_map.current.layers();

        layers[LAYER_KEYS.GT].visible(props.gtLayerVisible);
        layers[LAYER_KEYS.PRED].visible(props.predLayerVisible);
        layers[LAYER_KEYS.TILE_STATUS].visible(props.tileStatusLayerVisible);

        if (props.predLayerVisible || props.tileStatusLayerVisible) {
            viewportRender(
                false,
                props.predLayerVisible,
                props.tileStatusLayerVisible,
                props.currentImage.id,
                props.currentAnnotationClass.id
            );
        }

        const interval = setInterval(() => {
            // Use up-to-date props on every tick!
            if (geojs_map.current && props.currentImage && props.currentAnnotationClass) {
                if (props.predLayerVisible || props.tileStatusLayerVisible) {
                    viewportRender(
                        false,
                        props.predLayerVisible,
                        props.tileStatusLayerVisible,
                        props.currentImage.id,
                        props.currentAnnotationClass.id
                    ).then(() => {
                        console.log("Completed viewport render triggered by interval.");
                    });
                }
            }
        }, RENDER_PREDICTIONS_INTERVAL);

        return () => clearInterval(interval); // Cleanup on unmount
    }, [props.gtLayerVisible, props.predLayerVisible, props.tileStatusLayerVisible, props.currentImage, props.currentAnnotationClass]);

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