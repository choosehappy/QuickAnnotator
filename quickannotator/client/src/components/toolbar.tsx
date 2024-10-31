import {Button, ButtonGroup, ButtonToolbar} from "react-bootstrap";
import { Fullscreen, ArrowCounterclockwise, ArrowClockwise, Download, Cursor, Brush, Magic, Eraser, Heptagon } from 'react-bootstrap-icons';
import React from "react";
const Toolbar = React.memo(() => {

    const dividerStyle = {
        width: '1px',
        backgroundColor: '#ccc',
        margin: '0 10px', // Adjust spacing between groups
        height: '20px', // Full height to match ButtonToolbar
        display: 'inline-block', // Aligns with buttons
        alignSelf: 'center', // Centers within the toolbar if using flex
    };

    const buttonClass = "btn btn-primary";

    return (
        <ButtonToolbar aria-label="Toolbar with button groups">
            <ButtonGroup className="me-2" aria-label="First group">
                <input type="radio" className="btn-check" name="options" id="option1" autoComplete="off" checked/>
                <label className="btn btn-secondary" htmlFor="option1"><Fullscreen/></label>

                <input type="radio" className="btn-check" name="options" id="option2" autoComplete="off"/>
                <label className="btn btn-secondary" htmlFor="option2"><ArrowCounterclockwise/></label>

                <input type="radio" className="btn-check" name="options" id="option3" autoComplete="off"/>
                <label className="btn btn-secondary" htmlFor="option3"><ArrowClockwise/></label>

                <input type="radio" className="btn-check" name="options" id="option4" autoComplete="off"/>
                <label className="btn btn-secondary" htmlFor="option4"><Download/></label>

                <input type="radio" className="btn-check" name="options" id="option5" autoComplete="off"/>
                <label className="btn btn-secondary" htmlFor="option5"><Cursor/></label>

                <input type="radio" className="btn-check" name="options" id="option6" autoComplete="off"/>
                <label className="btn btn-secondary" htmlFor="option6"><Brush/></label>

                <input type="radio" className="btn-check" name="options" id="option7" autoComplete="off"/>
                <label className="btn btn-secondary" htmlFor="option7"><Magic/></label>

                <input type="radio" className="btn-check" name="options" id="option8" autoComplete="off"/>
                <label className="btn btn-secondary" htmlFor="option8"><Eraser/></label>

                <input type="radio" className="btn-check" name="options" id="option9" autoComplete="off"/>
                <label className="btn btn-secondary" htmlFor="option9"><Heptagon/></label>
            </ButtonGroup>
        </ButtonToolbar>
    )
});

export default Toolbar;