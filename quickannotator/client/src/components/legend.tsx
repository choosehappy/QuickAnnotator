import React, { useState } from "react";
import Card from "react-bootstrap/Card";

interface Props {
    mouseCoords: { x: number, y: number };
}
const Legend = React.memo((props: Props) => {

    return (
        <Card style={{
            position: "absolute",
            bottom: 0,
            right: 0,
            backgroundColor: "rgba(255, 255, 255, 0.8)",
            borderColor: "rgba(0, 0, 0, 0.8)",
            borderRadius: 6,
            zIndex: 10,
        }}>
            <Card.Body style={{ padding: "0.2em" }}>
                <div style={{ fontSize: "0.9em", color: "gray" }}>
                    x: {props.mouseCoords.x}, y: {props.mouseCoords.y}
                </div>
            </Card.Body>
        </Card>
    )
});

export default Legend;