import * as React from 'react';
import {Column, GridOption, SlickgridReactInstance, SlickgridReact} from "slickgrid-react";
import { Modal, Container, Row, Col, Card, ButtonToolbar, ButtonGroup, Button, ListGroup } from "react-bootstrap";

import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';
import { Image, Project } from "../../types.ts";
import { fetchImageByProjectId } from "../../helpers/api.ts"
fetchImageByProjectId
interface Props {
    project: Project;
    images: Image[];
    changed: boolean;
    containerId: string;
}

export default class ImageTable extends React.PureComponent {
    constructor(public props: Props){
        super(props);
        this.gridRef = React.createRef();
        this.state = {
            gridOptions: undefined,
            columnDefinitions: [],
            dataset: [],
            reactGrid: undefined
        };
    }

    componentDidMount() {
        // define the grid options & columns and then create the grid itself
        this.defineGrid();
    }
    componentDidUpdate(prevProps: Props) {
        console.log('update')
        if (prevProps.images !== this.props.images) {
            this.setState(() => ({
                ...this.state,
                dataset: this.getData(this.props.images),
            }));
        }
        if (prevProps.changed !== this.props.changed) {
            this?.gridRef?.current?.resizerService?.resizeGrid(5);
        }
        
    }


    reactGridReady(reactGrid: SlickgridReactInstance) {
        this.reactGrid = reactGrid;
    }

    defineGrid() {
        const thumbnailFormatter =  (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
            
            return `<a target="_blank" href="http://localhost:5173/project/${this.props.project.id}/annotate/${value}"><img src='http://localhost:5000/api/v1/image/${value}/2/file' height='64'></img></a>`
        }
        const actionFormatter =  (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
            // React.createElement(Button,{className:"", })
            return `<button>Delete</button>`
        }
        const tilesizeFormatter =  (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
            return value
        }
        const columns: Column[] = [
            { id: 'thumbnail', name: '', field: 'id', sortable: true, formatter: thumbnailFormatter},
            { id: 'id', name: 'Id', field: 'id', sortable: true},
            { id: 'name', name: 'Name', field: 'name', sortable: true},
            { id: 'width', name: 'Width', field: 'width', sortable: true},
            { id: 'height', name: 'Height', field: 'height', sortable: true},
            { id: 'dz_tilesize', name: 'DZ Tile Size', field: 'dz_tilesize', sortable: true },
            { id: 'date', name: 'Date', field: 'date', sortable: true },
            { id: 'action', name: '', field: 'action', sortable: true, formatter: actionFormatter  }
        ];

        const gridOptions: GridOption = {
            enableAutoResize: true,
            autoHeight: true,
            rowHeight: 64,
            resizeSensitivity: true,
            forceFitColumns:true,
            autoResize: {
                container: `#${this.props.containerId}`,
                // maxHeight: 200,
                // minWidth: 10
            },

        };



        this.setState(() => ({
            ...this.state,
            columnDefinitions: columns,
            gridOptions,
            dataset: [],
        }));

    }

    getData(images: Image[]) {
        const mappedData = images.map((img) => {
            return {
                id: img.id,
                name: img.name,
                width: img.width,
                height: img.height,
                embeddingCoord: img.embeddingCoord,
                group_id: img.group_id,
                dz_tilesize: img.dz_tilesize,
                date: img.datetime,
            };
        });

        return mappedData;
    }

    render() {
        return !this.state.gridOptions ? '' : (
            <SlickgridReact ref={this.gridRef} gridId={this.props.containerId + '-grid'}
                            columnDefinitions={this.state.columnDefinitions}
                            gridOptions={this.state.gridOptions}
                            dataset={this.state.dataset}
                            onReactGridCreated={$event => this.reactGridReady($event.detail)}
            />
        );
    }
}

