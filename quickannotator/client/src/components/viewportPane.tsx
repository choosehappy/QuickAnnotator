import Card from 'react-bootstrap/Card';
import React, { useEffect, useState, useRef } from 'react';
import geo from "geojs"
import { Annotation, Image, AnnotationClass, Tile } from "../types.ts"
import { ButtonToolbar, ButtonGroup, Button } from "react-bootstrap";
import { searchTiles } from "../helpers/api.ts";

interface Props {
    currentImage: Image | null;
    currentClass: AnnotationClass | null;
    gts: Annotation[];
    preds: Annotation[];
}

const ViewportPane = (props: Props) => {
    const viewRef = useRef(null);
    const [tileQueue, setTileQueue] = useState<Tile[] | null>(null);
    const geojs_map: geo.map | null = useRef(null);
    let zoomPanTimeout = null;

    function updateTileQueue(x1: number, y1: number, x2: number, y2: number) {
        if (!props.currentImage || !props.currentClass) return;
        searchTiles(props.currentImage.id, props.currentClass.id, x1, y1, x2, y2).then((tiles) => {
            // setTileQueue(tiles);
            console.log(tiles);
        });
    }

    const handleZoomPan = () => {
        console.log('Zooming or Panning...');
        // Clear the previous timeout if the zoom continues
        if (zoomPanTimeout) clearTimeout(zoomPanTimeout);

        // Set a new timeout to detect when zooming has stopped
        zoomPanTimeout = setTimeout(() => {
            console.log('Zooming or Panning stopped.');
            const bounds = geojs_map.current.bounds();
            updateTileQueue(bounds.left, bounds.bottom, bounds.right, bounds.top);
        }, 100); // Adjust this timeout duration as needed
    };

    useEffect(() => {
        const img = props.currentImage;
        console.log("Viewport detected image update.")
        if (img) {
            const params = geo.util.pixelCoordinateParams(
                viewRef.current, img.width, img.height, img.dz_tilesize, img.dz_tilesize);
            geojs_map.current = geo.map(params.map);
            params.layer.url = `/api/v1/image/${img.id}/patch_file/{z}/{x}_{y}.png`;

            if (geojs_map.current) {
                geojs_map.current.createLayer('osm', params.layer)
                geojs_map.current.geoOn(geo.event.mousemove, function (evt: any) {
                    console.log("mouse moved");
                });
                geojs_map.current.geoOn(geo.event.zoom, handleZoomPan)
                geojs_map.current.geoOn(geo.event.pan, handleZoomPan)
                console.log('Map initialized')
            }
        }


    }, [props.currentImage])

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