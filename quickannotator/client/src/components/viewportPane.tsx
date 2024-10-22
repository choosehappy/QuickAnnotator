import Card from 'react-bootstrap/Card';
import React, { useEffect, useState, useRef } from 'react';
import geo from "geojs"
import { Annotation, Image, AnnotationClass } from "../types.ts"
import {ButtonToolbar, ButtonGroup, Button} from "react-bootstrap";
interface Props {
    currentImage: Image | null;
    currentClass: AnnotationClass | null;
    gts: Annotation[];
    preds: Annotation[];
}

const ViewportPane = (props: Props) => {
    const viewRef = useRef(null);
    const [tileQueue, setTileQueue] = useState(null);

    /*  Option 1: sequential
    *   1. Get all tiles and insert into queue
    *   2. For each item in the queue, get the status
    *       0: If unseen, call /compute and push the item to the end of the queue.
    *       1: If processing, do nothing and push to the end of the queue.
    *       2: If seen, fetch annotations and remove tile from queue.
    *  */

    /*  Option 2: parallel
    *   1. Get all
    * */


    async function populateTileQueue(annotationClassId: number, imageId: number) {
        /*  Fetch all tiles within the viewport and set the tileQueue.
        *     */


        return
    }

    async function getTileStatus(tileId: number) {
        /*  Check if a tile is seen.
        *   1. Check if tile is seen
        *       a. 0: tile not seen. Call /compute, push tile idx to end of queue
        *       b. 1: tile currently being processed. Push tile to end of queue.
        *       c. 2: tile seen. Remove tile from queue and
        *   2.
        * */
    }

    async function getTileAnnotations(tileId: number) {

    }

    function handleMouseUp() {

    }

    useEffect(() => {
        const img = props.currentImage;
        console.log("Viewport detected image update.")
        if (props.currentImage) {
            const params = geo.util.pixelCoordinateParams(
                viewRef.current, img.width, img.height, img.dz_tilesize, img.dz_tilesize);
            const geojs_map = geo.map(params.map);

            params.layer.url = `/api/v1/image/${img.id}/patch_file/{z}/{x}_{y}.png`;
            geojs_map.createLayer('osm', params.layer)
            geojs_map.geoOn(geo.event.mousemove, function (evt: any) {
                console.log(evt.geo.x.toFixed(6), evt.geo.y.toFixed(6));
            });
            geojs_map.geoOn(geo.event.mouseup, function (evt: any) {

            })

            console.log('Map initialized')
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