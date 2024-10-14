import React, {useState, useEffect} from 'react';
import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';

import {
    SlickgridReactInstance,
    FieldType,
    Formatter,
    GridOption,
    Column,
    Formatters,
    SlickgridReact,
} from 'slickgrid-react';


const AnnotationList = () => {


    const [gridOptions, setGridOptions] = useState<GridOption | undefined>(undefined);
    const [dataset, setDataset] = useState([]);
    const [columnDefs, setColumnDefs] = useState<Column[]>([]);



    useEffect(() => {
        const initialGridOptions = {
            enableAutoResize: false,
            autoHeight: true,
        };

        setGridOptions(initialGridOptions);

        const initialData = [{
            id: 1,
            thumbnail: "placeholder",
            area: 1,
            centroid: "placeholder",
            class: "placeholder",
        }]

        setDataset(initialData);

        const columnDefinitions = [
            { id: 'thumbnail', name: 'Thumbnail', field: 'thumbnail', sortable: true, maxWidth: 100 },
            { id: 'area', name: 'Area', field: 'area', sortable: true, maxWidth: 100 },
            { id: 'centroid', name: 'Centroid', field: 'centroid', sortable: true, maxWidth: 100 },
            { id: 'class', name: 'Class', field: 'class', sortable: true, maxWidth: 100 },
        ];

        setColumnDefs(columnDefinitions);

    }, []);

    return (
        <div style={{height:'100px'}}>
            <SlickgridReact gridId={"grid1"}
                            columnDefinitions={columnDefs}
                            dataset={dataset}
                            gridOptions={gridOptions}/>
        </div>

    )
}

export default AnnotationList;