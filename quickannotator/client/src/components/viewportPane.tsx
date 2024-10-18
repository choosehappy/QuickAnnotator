import Card from 'react-bootstrap/Card';
import React, { useEffect, useState, useRef } from 'react';
import geo from "geojs"
import Annotation from "../types/annotations.ts";
import Image from "../types/image.ts";
import AnnotationClass from "../types/annotationClass.ts";

interface Props {
    currentImage: Image | null;
    selectedClass: AnnotationClass | null;
    gts: Annotation[];
    preds: Annotation[];
}

const ViewportPane = (props: Props) => {
    const viewRef = useRef(null);
    const [tileQueue, setTileQueue] = useState(null);




    async function populateTileQueue(annotationClassId: number, imageId: number) {
        /*  Fetch all tiles within the viewport and set the tileQueue.  */
        return
    }

    async function getTileStatus(tileId: number) {
        /*  Check if a tile is seen.
        *   1. Check if tile is seen
        *       a. 0: tile not seen. Call /compute
        *       b. 1: tile currently being processed. Add tile id to polling queue.
        *       c. 2: tile seen.
        *   2.
        * */
    }

    async function getTileAnnotations(tileId: number)

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