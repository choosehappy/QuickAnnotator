import React, { useState } from "react";
import Card from "react-bootstrap/Card";

interface Props {
    mouseCoords: { x: number, y: number };
}

const Legend = React.memo((props: Props) => {

    return (
        <Card style={{
            position: "absolute",
            bottom: 10,
            right: 10,
            backgroundColor: "rgba(255, 255, 255, 0.8)",
            borderColor: "rgba(0, 0, 0, 0.8)",
            borderRadius: 6,
            zIndex: 10,
        }}>
            <Card.Header>
                <h6 style={{ margin: 0 }}>Legend</h6>
            </Card.Header>
            <Card.Body>
                <div style={{ marginTop: "10px", fontSize: "0.9em", color: "gray" }}>
                    x: {props.mouseCoords.x}, y: {props.mouseCoords.y}
                </div>
            </Card.Body>
        </Card>
    )
});

export default Legend;