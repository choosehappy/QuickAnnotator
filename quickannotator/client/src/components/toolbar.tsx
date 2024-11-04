import ButtonGroup from 'react-bootstrap/ButtonGroup';
import ToggleButton from 'react-bootstrap/ToggleButton';
import {Button, ButtonToolbar} from 'react-bootstrap';
import { Fullscreen, ArrowCounterclockwise, ArrowClockwise, Download, Cursor, Brush, Magic, Eraser, Heptagon } from 'react-bootstrap-icons';
import React, { useState } from "react";
import {Annotation} from "../types.ts";

interface Props {
    currentTool: string;
    setCurrentTool: (currentTool: string | null) => void;
}

const Toolbar = React.memo((props: Props) => {

    const dividerStyle = {
        width: '1px',
        backgroundColor: '#ccc',
        margin: '0 10px', // Adjust spacing between groups
        height: '20px', // Full height to match ButtonToolbar
        display: 'inline-block', // Aligns with buttons
        alignSelf: 'center', // Centers within the toolbar if using flex
    };

    const buttons = [
        { icon: <Fullscreen/>},
        { icon: <ArrowCounterclockwise/>},
        { icon: <ArrowClockwise/>},
    ]

    const radios = [
        { icon: <Cursor/>},
        { icon: <Download/>},
        { icon: <Brush/>},
        { icon: <Magic/>},
        { icon: <Eraser/>},
        { icon: <Heptagon/>},
    ];

    return (
        <ButtonToolbar aria-label="Toolbar with button groups">
            <ButtonGroup className={"me-2"}>
                {buttons.map((button, idx) => (
                    <Button key={idx} variant="secondary" onClick={() => props.setCurrentTool(null)}>{button.icon}</Button>
                ))}
            </ButtonGroup>
            <ButtonGroup className={"me-2"}>
                {radios.map((radio, idx) => (
                    <ToggleButton
                        key={idx}
                        id={`radio-${idx}`}
                        type="radio"
                        variant="secondary"
                        name="radio"
                        value={idx}
                        checked={props.currentTool === idx.toString()}
                        onChange={(e) => props.setCurrentTool(e.currentTarget.value)}
                    >
                        {radio.icon}
                    </ToggleButton>
                ))}
            </ButtonGroup>
        </ButtonToolbar>
    )
});

export default Toolbar;