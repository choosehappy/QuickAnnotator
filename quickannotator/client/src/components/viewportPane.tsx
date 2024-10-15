import Card from 'react-bootstrap/Card';
import React, { useEffect, useState, useRef } from 'react';
import geo from "geojs"
import Annotation from "../types/annotations.ts";
import Image from "../types/image.ts";

const ViewportPane = () => {
    const viewRef = useRef(null);
    const [annotations, setAnnotations] = useState<Annotation[]>([]);
    const [map, setMap] = useState<geo.map | null>(null)
    const [image, setImage] = useState<Image | null>(null)

    async function getImage(image_id: number) {
        const queryString = new URLSearchParams({"image_id": image_id.toString()})
        return fetch(`/api/v1/image?${queryString}`,{
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(res => {
            res.json()
        });
    }

    useEffect(() => {
        const initializeMap = async () => {
            await getImage(1).then((resp) => {
                setImage(resp)
            })
            const params = geo.util.pixelCoordinateParams(
                viewRef.current, image?.width, image?.height, image?.dz_tilesize, image?.dz_tilesize);
            const map = geo.map(params.map);
            setMap(map);
            params.layer.url = `/image/tile/{z}/{x}/{y}`;
            map.createLayer('osm', params.layer)
            map.geoOn(geo.event.mousemove, function (evt: any) {
                console.log(evt.geo.x.toFixed(6), evt.geo.y.toFixed(6));
            });
            return null;
        };

        initializeMap().then(r => console.log('Map initialized'));
    }, []);

    return (
        <Card className="flex-grow-1">
            <Card.Body>
                <div ref={viewRef}>

                </div>
            </Card.Body>
        </Card>
    )
}

export default ViewportPane;