import React from 'react';
import Popover from 'react-bootstrap/Popover';
import { PopoverData } from '../types';

const tooltipStyle: React.CSSProperties = {
    textAlign: 'left',
};

export const renderTooltip = (content: PopoverData) => (
    <Popover id="button-popover" style={tooltipStyle}>
        <Popover.Header as="h3">{content.title}</Popover.Header>
        <Popover.Body style={{ whiteSpace: "pre-line" }}>
            {content.body}
        </Popover.Body>
    </Popover>
);