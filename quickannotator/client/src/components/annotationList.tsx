import * as React from 'react';
import {Column, GridOption, SlickgridReactInstance, SlickgridReact, } from "slickgrid-react";
import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';
import { Annotation, CurrentAnnotation, constructCurrentAnnotation } from "../types.ts";

interface Props {
    annotations: Annotation[];
    containerId: string;
    currentAnnotation: CurrentAnnotation;
    setCurrentAnnotation: React.Dispatch<React.SetStateAction<CurrentAnnotation | null>>;
}

export default class AnnotationList extends React.Component<Props, any> {
    constructor(public props: Props){
        super(props);

        this.state = {
            gridOptions: undefined,
            columnDefinitions: [],
            dataset: [],
            reactGrid: undefined,
        };
    }

    componentDidMount() {
        // define the grid options & columns and then create the grid itself
        this.defineGrid();
    }

    componentDidUpdate(prevProps: Props) {
        this.checkAnnotations(prevProps);
        // // If the current annotation changed
        // const currentAnnotation = this.props.currentAnnotation;
        // const previousAnnotation = prevProps.currentAnnotation;
        // if (currentAnnotation) {
        //     if (!previousAnnotation || !currentAnnotation.undoStack || !previousAnnotation.undoStack || currentAnnotation.undoStack.at(-1).id !== previousAnnotation.undoStack.at(-1).id) {
        //         // this.reactGrid?.gridService.setSelectedRow(currentAnnotation.id);
        //         console.log('highlighted item in slickgrid');
        //     }
        // }
    }

    checkAnnotations(prevProps: Props) {
        if (prevProps.annotations !== this.props.annotations) {
            this.setState(() => ({
                ...this.state,
                dataset: this.props.annotations,
            }));
        }
    }

    handleClick(e: CustomEvent) {
        console.log('Clicking on row e')
        const clickedRowIndex = e.detail.args.row;
        const annotation = this.state.reactGrid?.dataView.getItem(clickedRowIndex);

        this.props.setCurrentAnnotation(constructCurrentAnnotation(annotation));

        console.log('Clicked annotation:', annotation);
    }

    reactGridReady(reactGrid: SlickgridReactInstance) {
        this.setState({ reactGrid });
    }

    defineGrid() {

        const polygonFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
            // const svg =
            const geojson = JSON.parse(value);

            const coordinates = geojson.coordinates[0];
            // Find min and max coordinates for scaling
            const xCoords = coordinates.map(coord => coord[0]);
            const yCoords = coordinates.map(coord => coord[1]);
            const minX = Math.min(...xCoords);
            const maxX = Math.max(...xCoords);
            const minY = Math.min(...yCoords);
            const maxY = Math.max(...yCoords);

            // Calculate scaling factor to fit within 100x100 SVG dimensions
            const scale = Math.min(20 / (maxX - minX), 20 / (maxY - minY));

            // Scale coordinates to fit within SVG
            const points = coordinates.map(coord => {
                const x = (coord[0] - minX) * scale;
                const y = (coord[1] - minY) * scale;
                return `${x},${y}`;
            }).join(' ');

            // Construct SVG with scaled points
            const svg = `<svg width='100' height='20'><polygon points='${points}' style='fill:lime;stroke:purple;stroke-width:1' /></svg>`;
            return svg;
        }

        const centroidXFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
            const geojson = JSON.parse(value);
            return geojson.coordinates[0]
        }

        const centroidYFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
            const geojson = JSON.parse(value);
            return geojson.coordinates[1]}

        const columns: Column[] = [
            { id: 'thumbnail', name: 'Thumbnail', field: 'polygon', sortable: true, minWidth: 100, formatter: polygonFormatter },
            { id: 'area', name: 'Area', field: 'area', sortable: true, minWidth: 100 },
            { id: 'centroidX', name: 'CentroidX', field: 'centroid', sortable: true, minWidth: 100, formatter: centroidXFormatter},
            { id: 'centroidY', name: 'CentroidY', field: 'centroid', sortable: true, minWidth: 100, formatter: centroidYFormatter},
            { id: 'class', name: 'Class', field: 'annotation_class_id', sortable: true, minWidth: 100 },
        ];

        const gridOptions: GridOption = {
            enableAutoResize: true,
            autoResize: {
                container: '#' + this.props.containerId,
                maxHeight: 200,
                minWidth: 10,
            },

        };



        this.setState(() => ({
            ...this.state,
            columnDefinitions: columns,
            gridOptions,
            dataset: [],
        }));

    }

    render() {
        return !this.state.gridOptions ? '/' : (
            <SlickgridReact gridId={this.props.containerId + '-grid'}
                            columnDefinitions={this.state.columnDefinitions}
                            gridOptions={this.state.gridOptions}
                            dataset={this.state.dataset}
                            onReactGridCreated={$event => this.reactGridReady($event.detail)}
                            onClick={$event => this.handleClick($event)}
            />
        );
    }
}

