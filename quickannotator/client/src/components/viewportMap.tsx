import React, { useEffect, useState, useRef, useCallback, act } from 'react';
import geo from "geojs"
import { Annotation, Image, AnnotationClass, Tile, CurrentAnnotation, PutAnnArgs, AnnotationResponse } from "../types.ts"
import { searchTileIds, fetchAllAnnotations, postAnnotations, operateOnAnnotation, putAnnotation, removeAnnotation, getAnnotationsForTileIds, predictTile, getAnnotationsWithinPolygon, searchTileIdsWithinPolygon, fetchTileBoundingBox, fetchImageMetadata } from "../helpers/api.ts";
import { Point, Polygon, Feature, Position, GeoJsonGeometryTypes } from "geojson";

import { TOOLBAR_KEYS, INTERACTION_MODE, LAYER_KEYS, TILE_STATUS, MODAL_DATA, RENDER_PREDICTIONS_INTERVAL, RENDER_DELAY, MAP_TRANSLATION_DELAY, MASK_CLASS_ID, COOKIE_NAMES, POLYGON_OPERATIONS, POLYGON_CREATE_STYLE, POLYGON_CREATE_STYLE_SECONDARY, IMPORT_CREATE_STYLE, BRUSH_CREATE_STYLE, BRUSH_CREATE_STYLE_SECONDARY, BRUSH_SIZE, UI_SETTINGS } from "../helpers/config.ts";

import { computeTilesToRender, getTileFeatureById, redrawTileFeature, createGTTileFeature, createPredTileFeature, createPendingTileFeature, getFeatIdsRendered, tileIdIsValid, getScaledSize, createCirclePolygon, createConnectingRectangle } from '../utils/map.ts';
import { useCookies } from 'react-cookie';
import { useSearchParams, useNavigate } from "react-router-dom";
import { useHotkeys, isHotkeyPressed } from 'react-hotkeys-hook';


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
    activeModal: number | null;
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
    setMouseCoords: React.Dispatch<React.SetStateAction<{ x: number, y: number } | null>>;
}

const ViewportMap = (props: Props) => {
    const viewRef = useRef(null);
    const geojs_map = useRef<geo.map | null>(null);
    const polygonClicked = useRef<Boolean>(false);  // We need this to ensure polygon clicked and background clicked are mutually exclusive, because geojs does not provide control over event propagation.
    const activeRenderGroundTruthsCall = useRef<number>(0);
    const activeRenderPredictionsCall = useRef<number>(0);
    const featureIdsToUpdate = useRef<number[]>([]);
    const [cookies, setCookies] = useCookies([COOKIE_NAMES.SKIP_CONFIRM_IMPORT]);
    const [searchParams, setSearchParams] = useSearchParams();
    const lastBrushState = useRef<{ stateId: number, coords: [Position] } | null>(null);

    let zoomPanTimeout: any = null;

    const renderGTAnnotations = async (
        activeCallRef: React.MutableRefObject<number>
    ) => {

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

        const bounds = geojs_map.current.bounds();
        const x1 = bounds.left;
        const y1 = Math.abs(bounds.top);
        const x2 = bounds.right;
        const y2 = Math.abs(bounds.bottom);

        const currentCallToken = ++activeCallRef.current;
        const resp = await searchTileIds(props.currentImage.id, props.currentAnnotationClass.id, x1, y1, x2, y2, true);
        const tileIds = resp.data.tile_ids;
        const layer = geojs_map.current.layers()[LAYER_KEYS.GT];
        const tilesRendered = getFeatIdsRendered(layer, 'annotation');
        const { tilesToRemove, tilesToRender } = computeTilesToRender(tilesRendered, tileIds);

        tilesToRemove.forEach((tile_id) => {
            removeFeatureById(layer, tile_id);
        });

        let anns: Annotation[] = [];
        for (const tileId of tileIds) {
            if (tilesToRender.has(tileId)) {
                if (currentCallToken !== activeCallRef.current) return;
                console.log(`Processing tile ${tileId}`);
                const resp = await getAnnotationsForTileIds(props.currentImage.id, props.currentAnnotationClass.id, [tileId], true);
                const annotations = resp.data.map(annResp => new Annotation(annResp, props.currentAnnotationClass.id));
                if (currentCallToken !== activeCallRef.current) return;
                anns = anns.concat(annotations);
                const feature = createGTTileFeature({ tile_id: tileId }, annotations, layer, props.currentAnnotationClass, props.currentAnnotation?.currentState?.id,);
                feature.geoOn(geo.event.feature.mousedown, handleMousedownOnPolygon);
            } else {
                const webGLFeature = getTileFeatureById(layer, tileId);
                if (featureIdsToUpdate.current.includes(tileId)) {
                    const resp = await getAnnotationsForTileIds(props.currentImage.id, props.currentAnnotationClass.id, [tileId], true);
                    const data = resp.data.map(annResp => new Annotation(annResp, props.currentAnnotationClass.id));
                    redrawTileFeature(webGLFeature, {}, data);
                }
                const data: Annotation[] = webGLFeature.data();
                anns = anns.concat(data);
            }
            props.setGts(anns);
        }
    };

    const renderPredAnnotations = async (
        activeCallRef: React.MutableRefObject<number>
    ) => {
        // Predicted annotations are irrelevant if the current class is the mask class
        if (!props.currentImage || !props.currentAnnotationClass || props.currentAnnotationClass.id === MASK_CLASS_ID || !geojs_map.current) return;

        const bounds = geojs_map.current.bounds();
        const x1 = bounds.left;
        const y1 = Math.abs(bounds.top);
        const x2 = bounds.right;
        const y2 = Math.abs(bounds.bottom);

        const currentCallToken = ++activeCallRef.current;
        const resp = await searchTileIds(props.currentImage.id, props.currentAnnotationClass.id, x1, y1, x2, y2, false);
        const tileIds = resp.data.tile_ids;
        const layer = geojs_map.current.layers()[LAYER_KEYS.PRED];

        const tilesRendered = getFeatIdsRendered(layer, 'annotation');
        const { tilesToRemove, tilesToRender } = computeTilesToRender(tilesRendered, tileIds);

        tilesToRemove.forEach((tile_id) => {
            removeFeatureById(layer, tile_id);
        });

        let anns: Annotation[] = [];
        for (const tileId of tileIds) {
            const resp = await predictTile(props.currentImage.id, props.currentAnnotationClass.id, tileId);
            if (resp.status === 200) {
                removeFeatureById(layer, tileId, 'pending');
                removeFeatureById(layer, tileId, 'annotation');
                const tile = resp.data;
                if (tile.pred_status === TILE_STATUS.DONEPROCESSING) {  // We only want to get predicted annotations if the tile status is DONEPROCESSING. 
                    if (currentCallToken !== activeCallRef.current) return;
                    console.log(`Processing tile ${tileId}`);
                    const resp = await getAnnotationsForTileIds(props.currentImage.id, props.currentAnnotationClass.id, [tileId], false);
                    const annotations = resp.data.map(annResp => new Annotation(annResp, props.currentAnnotationClass.id));
                    if (currentCallToken !== activeCallRef.current) return;
                    anns = anns.concat(annotations);
                    createPredTileFeature({ tile_id: tileId }, annotations, layer, props.currentAnnotationClass);
                } else {
                    // Get a polygon for the tile and plot it on the map.
                    if (currentCallToken !== activeCallRef.current) return;
                    const resp = await fetchTileBoundingBox(props.currentImage.id, props.currentAnnotationClass.id, tileId);
                    if (currentCallToken !== activeCallRef.current) return;
                    if (resp.status === 200) {
                        const bbox_polygon = resp.data.bbox_polygon;
                        createPendingTileFeature({ tile_id: tileId }, [bbox_polygon], layer);
                    }
                }
            }
            props.setPreds(anns);
        }
    };

    function drawCentroids(annotations: Annotation[], map: geo.map) {
        return;
    }

    function removeFeatureById(layer: geo.layer, featureId: number, type: string = 'annotation') {
        const feature = getTileFeatureById(layer, featureId, type);
        if (feature) {
            feature.data([]);
            layer.removeFeature(feature);
            feature.draw();
        }
    }

    function handleMousedownOnPolygon(evt) {
        console.log("Polygon clicked.")
        console.log(evt.data)
        polygonClicked.current = true;

        // Note: gets called even when clicking on an already selected polygon.
        props.setCurrentAndPreviousAnnotation(evt.data);

        setTimeout(() => {
            polygonClicked.current = false;
        }, 0);
    }

    const handleMousedown = (evt) => {
        const annotationLayer = geojs_map.current.layers()[LAYER_KEYS.ANN];
        const mode = annotationLayer.mode();
        console.log(`Mouse down detected. Mode: ${mode}`);


        if (!polygonClicked.current && props.currentAnnotation) {
            const currentState = props.currentAnnotation.currentState;
            const tile_id = currentState?.tile_id;
            if (tileIdIsValid(tile_id)) {
                props.setCurrentAndPreviousAnnotation(null);
            }
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

        if (!props.currentAnnotation) return;    // Delete operation only allowed if an annotation is selected.

        const currentState: Annotation | undefined = props.currentAnnotation.currentState;
        if (!currentState) {
            console.log("No current annotation state found.");
            return;
        }
        const tile_id = currentState.tile_id;

        const annotationId = currentState.id;

        const layer = geojs_map.current.layers()[LAYER_KEYS.GT];

        if (annotationId && props.currentImage && props.currentAnnotationClass && tileIdIsValid(tile_id)) {
            removeAnnotation(props.currentImage.id, props.currentAnnotationClass.id, annotationId, true).then(() => {
                const feature = getTileFeatureById(layer, tile_id);
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
        const tileId = currentState.tile_id;
        if (!tileIdIsValid(tileId)) {
            console.log("Tile ID not found.")
            return;
        }
        const feature = getTileFeatureById(layer, tileId);
        const data = feature.data();
        operateOnAnnotation(currentState, newPolygon, operation).then((resp) => {
            const newState = new Annotation(resp.data, currentState.annotation_class_id);
            if (resp.data.polygon === null) {
                // Remove the annotation from updated data and ground truths
                const updatedData: Annotation[] = data.filter((d: Annotation) => d.id !== currentState.id);
                const updatedGroundTruths = props.gts.filter((gt: Annotation) => gt.id !== currentState.id);

                props.setGts(updatedGroundTruths);
                redrawTileFeature(feature, {}, updatedData);

                // Call the deleteAnnotation API method
                if (props.currentImage && props.currentAnnotationClass && currentState.id) {
                    removeAnnotation(props.currentImage.id, props.currentAnnotationClass.id, currentState.id, true)
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

        postAnnotations(currentImage.id, currentAnnotationClass.id, [newPolygon]).then((resp) => {
            if (resp.status === 200) {
                const annotation = new Annotation(resp.data[0], currentAnnotationClass.id);
                const tile_id = annotation.tile_id;
                const layer = geojs_map.current.layers()[LAYER_KEYS.GT];
                if (!tileIdIsValid(tile_id)) {
                    console.log("Tile ID not found.")
                    return;
                }
                let feature = getTileFeatureById(layer, tile_id);
                if (feature) {
                    const data = feature.data();
                    const updatedData = data.concat(annotation);
                    redrawTileFeature(feature, {}, updatedData);
                } else {
                    feature = createGTTileFeature({ tile_id: tile_id }, [annotation], layer, currentAnnotationClass);
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
            const resp = await getAnnotationsWithinPolygon(currentImage.id, currentAnnotationClass.id, false, polygon);
            if (resp.status === 200) {
                const anns = resp.data.map((annResp: AnnotationResponse) => new Annotation(annResp, currentAnnotationClass.id));
                if (anns.length === 0) {
                    alert("No annotations selected within the lasso. Please try again.");
                }
                // Get the ids for the features to redraw
                // const tilesResp = await searchTileIdsWithinPolygon(currentImage.id, currentAnnotationClass.id, polygon, false);
                // if (tilesResp.status === 200) {
                //     const tileIds = tilesResp.data.tile_ids;
                //     featureIdsToUpdate.current = tileIds;
                //     props.setHighlightedPreds(anns);
                //     props.setActiveModal(MODAL_DATA.IMPORT_CONF.id);
                // } else {
                // Get the ids for the features to redraw
                setHighlightedPreds(anns);
                const tilesResp = await searchTileIdsWithinPolygon(currentImage.id, currentAnnotationClass.id, polygon, false);
                if (tilesResp.status === 200) {
                    const tileIds = tilesResp.data.tile_ids;
                    featureIdsToUpdate.current = tileIds;
                    if (cookies[COOKIE_NAMES.SKIP_CONFIRM_IMPORT]) {
                        postAnnotations(currentImage.id, currentAnnotationClass?.id, anns.map(ann => ann.parsedPolygon)).then(() => {
                            setHighlightedPreds(null);
                            renderGTAnnotations(activeRenderGroundTruthsCall).then(() => {
                                console.log("Ground truths rendered.");
                            });
                        });
                    } else {
                        // Open the import confirmation modal
                        setActiveModal(MODAL_DATA.IMPORT_CONF.id);
                    }
                } else {
                    console.log("No tiles found within the polygon.");
                }
                annotationLayer.mode('point');
                // }
            }
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
            renderGTAnnotations(activeRenderGroundTruthsCall).then(() => {
                console.log("Ground truths rendered.");
            });

            renderPredAnnotations(activeRenderPredictionsCall).then(() => {
                console.log("Predictions rendered.");
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

        const map = geo.map({ ...params.map, max: 20 });
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

        const groundTruthLayer = map.createLayer('feature', { features: ['polygon'] });
        const predictionsLayer = map.createLayer('feature', { features: ['polygon'] });

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
    }, [props.currentImage, props.currentAnnotationClass, props.currentTool, props.currentAnnotation, props.gts, props.ctrlHeld]);

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

        // Clear all existing annotations.
        props.setGts([]);
        props.setPreds([]);

        renderGTAnnotations(activeRenderGroundTruthsCall).then(() => {
            console.log("Ground truths rendered on initial load.");
        })

        const interval = setInterval(() => {
            // console.log("Interval triggered.");
            if (geojs_map.current && props.currentImage && props.currentAnnotationClass) {
                renderPredAnnotations(activeRenderPredictionsCall).then(() => {
                    console.log("Predictions rendered.");
                });
            }
        }, RENDER_PREDICTIONS_INTERVAL);

        return () => clearInterval(interval); // Cleanup on unmount
    }, [props.currentAnnotationClass]);


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
        const tile_id = currentState?.tile_id;
        const prevTileId = prevState?.tile_id;
        const annotationId = currentState?.id;
        const prevAnnotationId = prevState?.id;
        const layer = geojs_map.current?.layers()[LAYER_KEYS.GT];
        // If the current annotation is associated with a tile feature, "redraw" the feature.
        if (tileIdIsValid(tile_id)) {
            const feature = getTileFeatureById(layer, tile_id);
            redrawTileFeature(feature, { currentAnnotationId: currentState?.id });
            const undoStackLength = props.currentAnnotation?.undoStack.length;

            if (currentState && !polygonClicked.current && undoStackLength && undoStackLength === 1) {  // If the annotation was changed programmatically (not clicked), we center the map.
                const centroid = currentState.parsedCentroid;
                translateMap(centroid.coordinates[0], centroid.coordinates[1]);
            }
        }

        // If the previous current annotation is associated with a tile feature, "redraw" the old tile.
        if (tileIdIsValid(prevTileId) && prevTileId !== tile_id) {
            const feature = getTileFeatureById(layer, prevTileId);
            redrawTileFeature(feature);
        }

        // TODO: PUT is called even when the annotation has been deleted. The PUT fails, which is fine, but it's not efficient.
        if (prevAnnotationId && prevAnnotationId !== annotationId && props.currentImage && props.currentAnnotationClass) {
            putAnnotation(props.currentImage.id, props.currentAnnotationClass.id, prevState).then(() => {
                console.log("Annotation updated.")
            });
        }

    }, [props.currentAnnotation])

    useEffect(() => {
        const x = props.selectedPred?.currentState?.parsedCentroid?.coordinates[0];
        const y = props.selectedPred?.currentState?.parsedCentroid?.coordinates[1];
        if (x && y) translateMap(x, y);
    }, [props.selectedPred]);

    // When the highlighted predictions change, redraw the features
    useEffect(() => {
        if (!geojs_map.current || !props.currentImage || !props.currentAnnotationClass) return;

        const predLayer = geojs_map.current.layers()[LAYER_KEYS.PRED];
        if (!predLayer) return;
        const features = predLayer.features().filter((f: any) => f.featureType === 'polygon');
        const featuresToRedraw = features.filter((f: any) => featureIdsToUpdate.current.includes(f.props.tile_id));
        const highlightedPolyIds = props.highlightedPreds ? props.highlightedPreds.map(ann => ann.id) : null;

        featuresToRedraw.forEach((f: any) => {
            redrawTileFeature(f, highlightedPolyIds ? { highlightedPolyIds: highlightedPolyIds } : {});
        });
    }, [props.highlightedPreds]);


    useHotkeys('backspace, delete', handleDeleteAnnotation, [props.currentAnnotation, props.currentImage, props.currentAnnotationClass, props.gts]);
    useHotkeys('ctrl', (event) => {
        const isKeyDown = event.type === 'keydown';
        props.setCtrlHeld(isKeyDown);
        console.log(`Ctrl key ${isKeyDown ? 'down' : 'up'}.`);
        const annotationLayer = geojs_map.current?.layers()[LAYER_KEYS.ANN];
        const brushLayer = geojs_map.current?.layers()[LAYER_KEYS.BRUSH];
        if (!annotationLayer) return;

        switch (props.currentTool) {
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