import React, { useEffect, useState, useRef, useCallback } from 'react';
import geo from "geojs"
import { Annotation, Image, AnnotationClass, Tile, CurrentAnnotation, PutAnnArgs, AnnotationResponse } from "../types.ts"
import { searchTileIds, fetchAllAnnotations, postAnnotations, operateOnAnnotation, putAnnotation, removeAnnotation, getAnnotationsForTileIds, predictTile, getAnnotationsWithinPolygon, searchTileIdsWithinPolygon, fetchTileBoundingBox, fetchImageMetadata } from "../helpers/api.ts";
import { Point, Polygon, Feature, Position, GeoJsonGeometryTypes } from "geojson";
import { TOOLBAR_KEYS, LAYER_KEYS, TILE_STATUS, MODAL_DATA, RENDER_PREDICTIONS_INTERVAL, RENDER_DELAY, MAP_TRANSLATION_DELAY } from "../helpers/config.ts";

import { computeTilesToRender, getTileFeatureById, redrawTileFeature, createGTTileFeature, createPredTileFeature, createPendingTileFeature, getFeatIdsRendered } from '../utils/map.ts';

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
    highlightedPreds: Annotation[] | null;
    setHighlightedPreds: React.Dispatch<React.SetStateAction<Annotation[] | null>>;
    activeModal: number | null;
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
    setMouseCoords: React.Dispatch<React.SetStateAction<{ x: number, y: number } | null>>;
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
    const featureIdsToUpdate = useRef<number[]>([]);
    const ctx = useLocalContext({ ...props });
    let zoomPanTimeout: any = null;

    const renderGTAnnotations = async (
        x1: number, y1: number, x2: number, y2: number,
        activeCallRef: React.MutableRefObject<number>
    ) => {
        if (!props.currentImage || !props.currentClass) return;

        const currentCallToken = ++activeCallRef.current;
        const resp = await searchTileIds(props.currentImage.id, props.currentClass.id, x1, y1, x2, y2, true);
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
                const resp = await getAnnotationsForTileIds(props.currentImage.id, props.currentClass.id, [tileId], true);
                const annotations = resp.data.map(annResp => new Annotation(annResp, props.currentClass.id));
                if (currentCallToken !== activeCallRef.current) return;
                anns = anns.concat(annotations);
                const feature = createGTTileFeature({ tile_id: tileId }, annotations, layer, props.currentAnnotation?.currentState?.id, props.currentClass.id);
                feature.geoOn(geo.event.feature.mousedown, handleMousedownOnPolygon);
            } else {
                const webGLFeature = getTileFeatureById(layer, tileId);
                if (featureIdsToUpdate.current.includes(tileId)) {
                    const resp = await getAnnotationsForTileIds(props.currentImage.id, props.currentClass.id, [tileId], true);
                    const data = resp.data.map(annResp => new Annotation(annResp, props.currentClass.id));
                    redrawTileFeature(webGLFeature, {}, data);
                }
                const data: Annotation[] = webGLFeature.data();
                anns = anns.concat(data);
            }
            props.setGts(anns);
        }
    };

    const renderPredAnnotations = async (
        x1: number, y1: number, x2: number, y2: number,
        activeCallRef: React.MutableRefObject<number>
    ) => {
        if (!props.currentImage || !props.currentClass) return;

        const currentCallToken = ++activeCallRef.current;
        const resp = await searchTileIds(props.currentImage.id, props.currentClass.id, x1, y1, x2, y2, false);
        const tileIds = resp.data.tile_ids;
        const layer = geojs_map.current.layers()[LAYER_KEYS.PRED];

        const tilesRendered = getFeatIdsRendered(layer, 'annotation');
        const { tilesToRemove, tilesToRender } = computeTilesToRender(tilesRendered, tileIds);

        tilesToRemove.forEach((tile_id) => {
            removeFeatureById(layer, tile_id);
        });

        let anns: Annotation[] = [];
        for (const tileId of tileIds) {
            const resp = await predictTile(props.currentImage.id, props.currentClass.id, tileId);
            if (resp.status === 200) {
                removeFeatureById(layer, tileId, 'pending');
                removeFeatureById(layer, tileId, 'annotation');
                const tile = resp.data;
                if (tile.pred_status === TILE_STATUS.DONEPROCESSING) {  // We only want to get predicted annotations if the tile status is DONEPROCESSING. 
                    if (currentCallToken !== activeCallRef.current) return;
                    console.log(`Processing tile ${tileId}`);
                    const resp = await getAnnotationsForTileIds(props.currentImage.id, props.currentClass.id, [tileId], false);
                    const annotations = resp.data.map(annResp => new Annotation(annResp, props.currentClass.id));
                    if (currentCallToken !== activeCallRef.current) return;
                    anns = anns.concat(annotations);
                    createPredTileFeature({ tile_id: tileId }, annotations, layer);
                } else {
                    // Get a polygon for the tile and plot it on the map.
                    if (currentCallToken !== activeCallRef.current) return;
                    const resp = await fetchTileBoundingBox(props.currentImage.id, props.currentClass.id, tileId);
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
        const layer = geojs_map.current.layers()[LAYER_KEYS.GT];

        if (annotationId && currentImage && currentClass && tile_id) {
            removeAnnotation(currentImage.id, currentClass.id, annotationId, true).then(() => {
                const feature = getTileFeatureById(layer, tile_id);
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
        const layer = geojs_map.current.layers()[LAYER_KEYS.GT];
        const feature = getTileFeatureById(layer, currentState.tile_id);
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

        postAnnotations(currentImage.id, currentClass.id, [newPolygon]).then((resp) => {
            if (resp.status === 200) {
                const annotation = new Annotation(resp.data[0], currentClass.id);
                const tile_id = annotation.tile_id;
                const layer = geojs_map.current.layers()[LAYER_KEYS.GT];
                if (!tile_id) {
                    console.log("Tile ID not found.")
                    return;
                }
                const feature = getTileFeatureById(layer, tile_id);
                if (feature) {
                    const data = feature.data();
                    const updatedData = data.concat(annotation);
                    redrawTileFeature(feature, {}, updatedData);
                } else {
                    const feature = createGTTileFeature({}, [annotation], layer, currentClass.id);
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
            const resp = await getAnnotationsWithinPolygon(currentImage.id, currentClass.id, false, polygon2);
            if (resp.status === 200) {
                const anns = resp.data.map((annResp: AnnotationResponse) => new Annotation(annResp, currentClass.id));

                // Get the ids for the features to redraw
                const tilesResp = await searchTileIdsWithinPolygon(currentImage.id, currentClass.id, polygon2, false);
                if (tilesResp.status === 200) {
                    const tileIds = tilesResp.data.tile_ids;
                    featureIdsToUpdate.current = tileIds;
                    props.setHighlightedPreds(anns);
                    props.setActiveModal(MODAL_DATA.IMPORT_CONF.id);
                } else {
                    console.log("No tiles found within the polygon.");
                }
            } else {
                console.log("No annotations found within the polygon.");
            }



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
            renderGTAnnotations(x1, y1, x2, y2, activeRenderGroundTruthsCall).then(() => {
                console.log("Ground truths rendered.");
            });
            renderPredAnnotations(x1, y1, x2, y2, activeRenderPredictionsCall).then(() => {
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

    // UseEffect hook for rendering predictions periodically
    useEffect(() => {
        const interval = setInterval(() => {
            // console.log("Interval triggered.");
            if (geojs_map.current && props.currentImage && props.currentClass) {
                const bounds = geojs_map.current.bounds();
                const x1 = bounds.left;
                const y1 = Math.abs(bounds.top);
                const x2 = bounds.right;
                const y2 = Math.abs(bounds.bottom);
                renderPredAnnotations(x1, y1, x2, y2, activeRenderPredictionsCall).then(() => {
                    console.log("Predictions rendered.");
                });
            }
        }, RENDER_PREDICTIONS_INTERVAL);

        return () => clearInterval(interval); // Cleanup on unmount
    }, [props.currentClass]);

    // UseEffect hook to initialize the map
    useEffect(() => {
        const initializeMap = async () => {
            const img = props.currentImage;

            const params = geo.util.pixelCoordinateParams(
                viewRef.current, img.base_width, img.base_height, img.dz_tilesize, img.dz_tilesize);
            
            const map = geo.map({ ...params.map, max: 20 });
            params.layer.url = `/api/v1/image/${img.id}/patch_file/{z}/{x}_{y}.png`;
            console.log("OSM layer loaded.");

            const groundTruthLayer = map.createLayer('feature', { features: ['polygon'] });
            const predictionsLayer = map.createLayer('feature', { features: ['polygon'] });

            map.createLayer('osm', { ...params.layer, zIndex: 0 })

            const annotationLayer = map.createLayer('annotation',
                {
                    active: true,
                    zIndex: 2,
                });

            const uiLayer = map.createLayer('ui');

            // Fetch image metadata and set scale
            try {
                const metadataResp = await fetchImageMetadata(img.id);
                const mpp = metadataResp.data.mpp; // microns per pixel
                const micronUnits = [
                    { unit: 'µm', scale: 1 }, // for single micron
                ];
                uiLayer.createWidget('scale', {
                    position: { left: 10, bottom: 10 },
                    units: micronUnits,
                    scale: mpp,
                });
            } catch (error) {
                console.error("Failed to fetch image metadata:", error);
            }

            annotationLayer.geoOn(geo.event.mousedown, handleMousedown);
            annotationLayer.geoOn(geo.event.annotation.state, handleNewAnnotation);
            annotationLayer.geoOn(geo.event.annotation.mode, handleAnnotationModeChange);
            window.onkeydown = (evt) => {
                if (evt.key === 'Backspace' || evt.key === 'Delete') {
                    handleDeleteAnnotation(evt);
                }
            }

            map.geoOn(geo.event.mousemove, function (evt: any) { props.setMouseCoords({x: evt.geo.x.toFixed(2), y: evt.geo.y.toFixed(2) }) });
            map.geoOn(geo.event.zoom, handleZoomPan);
            map.geoOn(geo.event.pan, handleZoomPan);
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
        const layer = geojs_map.current?.layers()[LAYER_KEYS.GT];

        // If the current annotation is associated with a tile feature, "redraw" the feature.
        if (tile_id) {
            const feature = getTileFeatureById(layer, tile_id);
            redrawTileFeature(feature, { currentAnnotationId: currentState?.id });

            if (!polygonClicked.current) {  // The polygon was selected from the ground truth list.
                const centroid = currentState.parsedCentroid;
                translateMap(centroid.coordinates[0], centroid.coordinates[1]);
            }
        }

        // If the previous current annotation is associated with a tile feature, "redraw" the old tile.
        if (prevTileId && prevTileId !== tile_id) {
            const feature = getTileFeatureById(layer, prevTileId);
            redrawTileFeature(feature);
        }

        // TODO: PUT is called even when the annotation has been deleted. The PUT fails, which is fine, but it's not efficient.
        if (prevAnnotationId && prevAnnotationId !== annotationId && props.currentImage && props.currentClass) {
            putAnnotation(props.currentImage.id, props.currentClass.id, prevState).then(() => {
                console.log("Annotation updated.")
            });
        }

    }, [props.currentAnnotation])

    // When the highlighted predictions change, redraw the features
    useEffect(() => {
        if (geojs_map.current && props.currentImage && props.currentClass) {
            const predLayer = geojs_map.current.layers()[LAYER_KEYS.PRED];
            const features = predLayer.features().filter((f) => f.featureType === 'polygon');
            const featuresToRedraw = features.filter((f) => featureIdsToUpdate.current.includes(f.props.tile_id));
            const highlightedPolyIds = props.highlightedPreds ? props.highlightedPreds.map(ann => ann.id) : null;

            featuresToRedraw.forEach((f) => {
                redrawTileFeature(f, highlightedPolyIds ? { highlightedPolyIds: highlightedPolyIds } : {});
            });

            const bounds = geojs_map.current.bounds();
            const x1 = bounds.left;
            const y1 = Math.abs(bounds.top);
            const x2 = bounds.right;
            const y2 = Math.abs(bounds.bottom);
            if (!highlightedPolyIds) {
                renderGTAnnotations(x1, y1, x2, y2, activeRenderGroundTruthsCall).then(() => {
                    console.log("Predictions rendered.");
                    featureIdsToUpdate.current = [];
                });
            }
        }

    }, [props.highlightedPreds])

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