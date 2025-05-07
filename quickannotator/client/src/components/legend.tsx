import React, { useState } from "react";
import Card from "react-bootstrap/Card";

interface Props {
    mouseCoords: number[];
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
                <ul style={{ margin: 0, padding: 0, listStyleType: "none" }}>
                    <li><span style={{ color: "red" }}>●</span> Ground Truth</li>
                    <li><span style={{ color: "blue" }}>●</span> Predictions</li>
                    <li><span style={{ color: "green" }}>●</span> Current Annotation</li>
                </ul>
            </Card.Body>
        </Card>
    )
});

export default Legend;