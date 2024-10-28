import Card from 'react-bootstrap/Card';
import React, { useEffect, useState, useRef } from 'react';
import geo from "geojs"
import { Annotation, Image, AnnotationClass, Tile } from "../types.ts"
import { ButtonToolbar, ButtonGroup, Button } from "react-bootstrap";
import { fetchTile, searchTiles, searchAnnotations } from "../helpers/api.ts";

interface Props {
    currentImage: Image | null;
    currentClass: AnnotationClass | null;
    gts: Annotation[];
    setGts: (gts: Annotation[]) => void;
    preds: Annotation[];
    setPreds: (preds: Annotation[]) => void;
}

const ViewportPane = (props: Props) => {
    const viewRef = useRef(null);
    const [dlTileQueue, setDlTileQueue] = useState<Tile[] | null>(null);
    const [geojs_map, setGeojsMap] = useState<geo.map | null>(null);
    let zoomPanTimeout = null;




    const renderAnnotationTest = async () => {
        if (!props.currentImage || !props.currentClass) return;
        const anns = await searchAnnotations(props.currentImage.id, props.currentClass.id, true, 0, 0, 10000, 10000)
        props.setGts(anns);
    }

    async function renderAnnotations(x1: number, y1: number, x2: number, y2: number) {
        if (!props.currentImage || !props.currentClass) return;
        const tiles = await searchTiles(props.currentImage.id, props.currentClass.id, x1, y1, x2, y2)
        let anns = [];
        for (const tile of tiles) {
            console.log(`Processing tile ${tile.id}`)
            const resp = await processTile(tile);
            anns = anns.concat(resp);
            props.setGts(anns);
        }
    }

    const processTile = async (tile: Tile) => {
        const t = await fetchTile(tile.id);
        const geom = JSON.parse(t.geom);    // for some reason the geom is stringified
        const tileState = t.seen;

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

    useEffect(() => {
        const handleZoomPan = () => {
            console.log('Zooming or Panning...');
            // Clear the previous timeout if the zoom continues
            if (zoomPanTimeout) clearTimeout(zoomPanTimeout);
            // Set a new timeout to detect when zooming has stopped
            zoomPanTimeout = setTimeout(() => {
                console.log('Zooming or Panning stopped.');
                const bounds = geojs_map.bounds();
                console.log(bounds);
                renderAnnotations(bounds.left, bounds.bottom, bounds.right, bounds.top);
                // renderAnnotationTest();
            }, 100); // Adjust this timeout duration as needed
        };

        const initializeMap = async () => {
            const img = props.currentImage;
            if (img && props.currentClass) {
                const params = geo.util.pixelCoordinateParams(
                    viewRef.current, img.width, img.height, img.dz_tilesize, img.dz_tilesize);
                const map = geo.map(params.map);
                setGeojsMap(map);
                params.layer.url = '/api/v1/image/1/patch_file/{z}/{x}_{y}.png';
                console.log("OSM layer loaded.")
                map.createLayer('feature', {features: ['polygon']});
                map.createLayer('osm', { ...params.layer, zIndex: 0 })

                map.geoOn(geo.event.mousemove, function (evt: any) {
                    console.log(`Mouse at x=${evt.geo.x}, y=${evt.geo.y}`);
                });
                map.geoOn(geo.event.zoom, handleZoomPan)
                map.geoOn(geo.event.pan, handleZoomPan)

                return null;
            }
        }
        if (props.currentImage && props.currentClass) {
            initializeMap().then(() => console.log(console.log(`Map initialized for ${geojs_map}`)));
        }

    }, [props.currentImage, props.currentClass]);


    useEffect(() => {
        const drawPolygons = async () => {
            console.log("Annotations detected update.")

            const feature = geojs_map.layers()[0].createFeature('polygon');

            const data = props.gts.map((a) => {
                const polygon = JSON.parse(a.polygon.toString());
                return polygon.geometry.coordinates[0];
            });

            feature
                .position((d) => {return {
                    x: d[0], y: d[1]};
                })
                // .polygon() should return the polygon.geometry.coordinates[0];
                .data(data)
                .style('fill', true)
                .style('fillOpacity', 0.9)
                .style('stroke', true).draw();
        }

        if (geojs_map && props.gts.length > 0 && props.gts.length < 10000) {
            drawPolygons().then(() => console.log("Feature layer initialized."));
        }
    }, [geojs_map, props.gts]);

    return (
        <Card className="flex-grow-1">
            <Card.Header style={{
                position: "absolute",
                top: 10,
                left: "50%",
                transform: "translate(-50%, 0%)",
                backgroundColor: "rgba(255, 255, 255, 0.6)",
                borderColor: "rgba(0, 0, 0, 0.8)",
                borderRadius: 6,
                zIndex: 10,
            }}>
                <ButtonToolbar aria-label="Toolbar with button groups">
                    <ButtonGroup className="me-2" aria-label="First group">
                        <Button>1</Button> <Button>2</Button> <Button>3</Button>{' '}
                        <Button>4</Button>
                    </ButtonGroup>
                    <ButtonGroup className="me-2" aria-label="Second group">
                        <Button>5</Button> <Button>6</Button> <Button>7</Button>
                    </ButtonGroup>
                    <ButtonGroup aria-label="Third group">
                        <Button>8</Button>
                    </ButtonGroup>
                </ButtonToolbar>
            </Card.Header>
            <Card.Body style={{padding: "0px"}}>
                <div ref={viewRef} style={
                    {
                        width: '100%',
                        height: '100%',
                        backgroundColor: 'white',
                        borderRadius: 6
                    }
                }>
                </div>
            </Card.Body>
        </Card>
    )
}

export default ViewportPane;