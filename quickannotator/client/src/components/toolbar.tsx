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
        { icon: <Fullscreen/>, disabled: true, title: "Fullscreen", shortcut: "F" },
        { icon: <ArrowCounterclockwise/>, disabled: true, title: "Undo", shortcut: "Ctrl+Z" },
        { icon: <ArrowClockwise/>, disabled: true, title: "Redo", shortcut: "Ctrl+Y" },
    ];

    const radios = [
        { icon: <Cursor/>, disabled: false, title: "Select", shortcut: "1" },
        { icon: <Download/>, disabled: false, title: "Import", shortcut: "2" },
        { icon: <Brush/>, disabled: true, title: "Brush", shortcut: "3" },
        { icon: <Magic/>, disabled: true, title: "Magic", shortcut: "4" },
        { icon: <Eraser/>, disabled: true, title: "Eraser", shortcut: "5" },
        { icon: <Heptagon/>, disabled: false, title: "Polygon", shortcut: "6" },
    ];
    const buttonStyle: React.CSSProperties = {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        minWidth: '48px',
        minHeight: '48px',
        justifyContent: 'center',
        fontSize: '1rem',
        gap: '2px',
        padding: '4px 8px',
    };

    const buttonTextStyle: React.CSSProperties = {
        fontSize: '0.5rem',
        marginTop: '2px',
        textAlign: 'center',
        fontWeight: 'bold',
    };

    const buttonShortcutStyle: React.CSSProperties = {
        fontSize: '0.75rem',
        marginTop: '2px',
        textAlign: 'center',
        fontWeight: 'bold',
        color: 'white',
    };

    return (
        <ButtonToolbar
            aria-label="Toolbar with button groups"
        >
            <ButtonGroup className={"me-2"}>
            {buttons.map((button, idx) => (
                <Button
                key={idx}
                variant="secondary"
                onClick={() => props.setCurrentTool(null)}
                disabled={button.disabled}
                style={buttonStyle}
                >
                {button.icon}
                <span style={buttonTextStyle}>
                    {button.title}
                </span>
                <span style={buttonShortcutStyle}>
                    {button.shortcut}
                </span>
                </Button>
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
                    disabled={radio.disabled}
                    style={buttonStyle}
                >
                    {radio.icon}
                    <span style={buttonTextStyle}>
                        {radio.title}
                    </span>
                    <span style={buttonShortcutStyle}>
                        {radio.shortcut}
                    </span>
                </ToggleButton>
            ))}
            </ButtonGroup>
        </ButtonToolbar>
    )
});

export default Toolbar;