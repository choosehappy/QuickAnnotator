import ButtonGroup from 'react-bootstrap/ButtonGroup';
import ToggleButton from 'react-bootstrap/ToggleButton';
import { Button, ButtonToolbar, OverlayTrigger, Popover } from 'react-bootstrap';
import Tooltip from 'react-bootstrap/Tooltip';
import React, { useState } from "react";
import { Annotation, PopoverData, ToolbarButton } from "../types.ts";
import { BRUSH_TOOL_HOTKEY, IMPORT_TOOL_HOTKEY, PAN_TOOL_HOTKEY, POLYGON_TOOL_HOTKEY, POPOVER_DATA, WAND_TOOL_HOTKEY } from "../helpers/config";
import { Fullscreen, ArrowCounterclockwise, ArrowClockwise, ArrowsMove, Cursor, Brush, Magic, Eraser, Heptagon, Bookmark, Bookmarks } from 'react-bootstrap-icons';
import { TOOLBAR_KEYS } from '../helpers/config.ts';

interface Props {
    currentTool: string | null;
    setCurrentTool: (currentTool: string | null) => void;
    ctrlHeld: boolean;
    gtLayerVisible: boolean;
    predLayerVisible: boolean;
    tileStatusLayerVisible: boolean;
    setGtLayerVisible: (visible: boolean) => void;
    setPredLayerVisible: (visible: boolean) => void;
    setTileStatusLayerVisible: (visible: boolean) => void;
}

const Toolbar = React.memo((props: Props) => {

    const buttons: ToolbarButton[] = [
        { icon: <Fullscreen />, disabled: true, title: "Fullscreen", shortcut: "F", content: POPOVER_DATA.FULLSCREEN_TOOL },
        { icon: <ArrowCounterclockwise />, disabled: true, title: "Undo", shortcut: "Ctrl+Z", content: POPOVER_DATA.UNDO_TOOL },
        { icon: <ArrowClockwise />, disabled: true, title: "Redo", shortcut: "Ctrl+Y", content: POPOVER_DATA.REDO_TOOL },
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

    const tooltipStyle: React.CSSProperties = {
        textAlign: 'left',
    };


    const renderTooltip = (content: PopoverData) => (
        <Popover id="button-popover" style={tooltipStyle}>
            <Popover.Header as="h3">{content.title}</Popover.Header>
            <Popover.Body>
                {content.description}
            </Popover.Body>
        </Popover>
    );
    const radios = {
        [TOOLBAR_KEYS.POINTER]: { icon: <Cursor/>, ctrlIcon: null, disabled: false, title: "Pan", shortcut: PAN_TOOL_HOTKEY, content: POPOVER_DATA.PAN_TOOL },
        [TOOLBAR_KEYS.IMPORT]: { icon: <Bookmark/>, ctrlIcon: <Bookmarks/>, disabled: false, title: "Import", shortcut: IMPORT_TOOL_HOTKEY, content: POPOVER_DATA.IMPORT_TOOL },
        [TOOLBAR_KEYS.BRUSH]: { icon: <Brush/>, ctrlIcon: <Eraser/>, disabled: false, title: "Brush", shortcut: BRUSH_TOOL_HOTKEY, content: POPOVER_DATA.BRUSH_TOOL },
        [TOOLBAR_KEYS.WAND]: { icon: <Magic/>, ctrlIcon: null, disabled: true, title: "Magic", shortcut: WAND_TOOL_HOTKEY, content: POPOVER_DATA.MAGIC_TOOL },
        [TOOLBAR_KEYS.POLYGON]: { icon: <Heptagon/>, ctrlIcon: <Eraser/>, disabled: false, title: "Polygon", shortcut: POLYGON_TOOL_HOTKEY, content: POPOVER_DATA.POLYGON_TOOL },
    };

    const layerToggles = [
        { key: 'gtLayerVisible', title: 'Ground Truth', getter: props.gtLayerVisible, setter: props.setGtLayerVisible },
        { key: 'predLayerVisible', title: 'Prediction', getter: props.predLayerVisible, setter: props.setPredLayerVisible },
        { key: 'tileStatusLayerVisible', title: 'Tile Status', getter: props.tileStatusLayerVisible, setter: props.setTileStatusLayerVisible },
    ];

    return (
        <ButtonToolbar
            aria-label="Toolbar with button groups"
        >
            <ButtonGroup className={"me-2"}>
                {buttons.map((button, idx) => (
                    <OverlayTrigger
                        placement="bottom"
                        overlay={renderTooltip(button.content)}
                        key={idx}
                    >
                        <Button
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
                    </OverlayTrigger>
                ))}
            </ButtonGroup>
            <ButtonGroup className={"me-2"}>
                {Object.entries(radios).map(([key, radio]) => (
                    <OverlayTrigger
                        key={key}
                        placement="bottom"
                        overlay={renderTooltip(radio.content)}
                    >
                    <ToggleButton
                        key={key}
                        id={`radio-${key}`}
                        type="radio"
                        variant="secondary"
                        name="radio"
                        value={key}
                        style={buttonStyle}
                        checked={props.currentTool === key}
                        onChange={(e) => {
                            props.setCurrentTool(e.currentTarget.value);
                            e.currentTarget.blur(); // Return focus to annotation page, allowing hotkey events to fire.
                        }}
                        disabled={radio.disabled}
                    >
                        {props.ctrlHeld && props.currentTool === key && radio.ctrlIcon ? radio.ctrlIcon : radio.icon}
                        <span style={buttonTextStyle}>
                            {radio.title}
                        </span>
                        <span style={buttonShortcutStyle}>
                            {radio.shortcut}
                        </span>
                    </ToggleButton>
                    </OverlayTrigger>
                ))}
            </ButtonGroup>
            <ButtonGroup className={"me-2"}>
                {layerToggles.map((toggle) => (
                    <ToggleButton
                        key={toggle.key}
                        id={`toggle-${toggle.key}`}
                        type="checkbox"
                        variant="secondary"
                        name="layerToggle"
                        value={toggle.key}
                        style={buttonStyle}
                        checked={toggle.getter}
                        onChange={(e) => toggle.setter(e.currentTarget.checked)}
                    >
                        <span style={buttonTextStyle}>{toggle.title}</span>
                    </ToggleButton>
                ))}
            </ButtonGroup>
        </ButtonToolbar>
    )
});

export default Toolbar;