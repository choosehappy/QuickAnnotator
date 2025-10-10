import ButtonGroup from 'react-bootstrap/ButtonGroup';
import ToggleButton from 'react-bootstrap/ToggleButton';
import {Button, ButtonToolbar} from 'react-bootstrap';
import { Fullscreen, ArrowCounterclockwise, ArrowClockwise, Download, Cursor, Brush, Magic, Eraser, Heptagon, Bookmark, Bookmarks } from 'react-bootstrap-icons';
import React, { useState } from "react";
import { TOOLBAR_KEYS } from '../helpers/config.ts';


interface Props {
    currentTool: string | null;
    setCurrentTool: (currentTool: string | null) => void;
    ctrlHeld: boolean;
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
        { icon: <Fullscreen/>, disabled: true },
        { icon: <ArrowCounterclockwise/>, disabled: true },
        { icon: <ArrowClockwise/>, disabled: true },
    ];

    const radios = {
        [TOOLBAR_KEYS.POINTER]: { icon: <Cursor/>, ctrlIcon: null, disabled: false },
        [TOOLBAR_KEYS.IMPORT]: { icon: <Bookmark/>, ctrlIcon: <Bookmarks/>, disabled: false },
        [TOOLBAR_KEYS.BRUSH]: { icon: <Brush/>, ctrlIcon: <Eraser/>, disabled: false },
        [TOOLBAR_KEYS.WAND]: { icon: <Magic/>, ctrlIcon: null, disabled: true },
        [TOOLBAR_KEYS.POLYGON]: { icon: <Heptagon/>, ctrlIcon: <Eraser/>, disabled: false },
    };

    return (
        <ButtonToolbar aria-label="Toolbar with button groups">
            <ButtonGroup className={"me-2"}>
                {buttons.map((button, idx) => (
                    <Button
                        key={idx}
                        variant="secondary"
                        onClick={() => props.setCurrentTool(null)}
                        disabled={button.disabled}
                    >
                        {button.icon}
                    </Button>
                ))}
            </ButtonGroup>
            <ButtonGroup className={"me-2"}>
                {Object.entries(radios).map(([key, radio]) => (
                    <ToggleButton
                        key={key}
                        id={`radio-${key}`}
                        type="radio"
                        variant="secondary"
                        name="radio"
                        value={key}
                        checked={props.currentTool === key}
                        onChange={(e) => {
                            props.setCurrentTool(e.currentTarget.value);
                            e.currentTarget.blur(); // Return focus to annotation page, allowing hotkey events to fire.
                        }}
                        disabled={radio.disabled}
                    >
                        {props.ctrlHeld && props.currentTool === key && radio.ctrlIcon ? radio.ctrlIcon : radio.icon}
                    </ToggleButton>
                ))}
            </ButtonGroup>
        </ButtonToolbar>
    )
});

export default Toolbar;