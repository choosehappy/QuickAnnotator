import React from 'react';
import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';


import {
    SlickgridReactInstance,
    Column,
    FieldType,
    Formatter,
    Formatters,
    GridOption,
    SlickgridReact,
} from 'slickgrid-react';

const AnnotationList = () => {
    const gridOptions = {
        gridWidth: 400,
        gridHeight: 400,
        enableAutoResize: false
    };

    const columnDefinitions = [
        { id: 'title', name: 'Title', field: 'title', sortable: true, minWidth: 100 },
        { id: 'duration', name: 'Duration (days)', field: 'duration', sortable: true, minWidth: 100 },
        { id: '%', name: '% Complete', field: 'percentComplete', sortable: true, minWidth: 100 },
        { id: 'start', name: 'Start', field: 'start', minWidth: 100 },
        { id: 'finish', name: 'Finish', field: 'finish', minWidth: 100 },
        { id: 'effort-driven', name: 'Effort Driven', field: 'effortDriven', sortable: true, minWidth: 100 }
    ];

    const data = [{
        id: 1,
        title: 'Title',
        duration: '1',
        percentComplete: '1',
        start: 'none',
        finish: 'none',
        effortDriven: 'none'
    }]

    return (
        <SlickgridReact gridId={"grid1"} columnDefinitions={columnDefinitions} dataset={data} gridOptions={gridOptions} />
    )
}

export default AnnotationList;