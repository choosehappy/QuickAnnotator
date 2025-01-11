import * as React from 'react';
import {Column, GridOption, SlickgridReactInstance, SlickgridReact, } from "slickgrid-react";
import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';
import { Annotation, CurrentAnnotation } from "../types.ts";
import { Point, Polygon, Position } from 'geojson';

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

        this.checkCurrentAnnotation(prevProps)
    }

    checkAnnotations(prevProps: Props) {
        if (prevProps.annotations !== this.props.annotations) {
            this.state.reactGrid?.gridService.resetGrid();
            this.setState(() => ({
                ...this.state,
                dataset: this.props.annotations,
            }));
        }
    }

    checkCurrentAnnotation(prevProps: Props) {
        if (this.props.currentAnnotation) {
            const currentAnn = this.props.currentAnnotation;
            const prevAnnId = prevProps.currentAnnotation?.currentState?.id;
            const currentAnnId = currentAnn?.currentState?.id;
            // IF the current annotation is not null and is new, scroll to the new annotation
            if (this.props.containerId === 'gt' && currentAnnId && prevAnnId !== currentAnnId) {
                const annotationId = currentAnn.currentState?.id;
                const annotationIndex = this.state.dataset.findIndex((annotation: Annotation) => annotation.id === annotationId);
                if (annotationId) {
                    this.state.reactGrid?.gridService.setSelectedRow(annotationIndex);
                    this.state.reactGrid?.slickGrid.scrollRowIntoView(annotationIndex);
                }
            }
        } else {

        }
    }


    handleClick(e: CustomEvent) {
        console.log('Clicking on row e')
        const clickedRowIndex = e.detail.args.row;
        const annotation = this.state.reactGrid?.dataView.getItem(clickedRowIndex);

        this.props.setCurrentAnnotation(new CurrentAnnotation(annotation));

        console.log('Clicked annotation:', annotation);
    }

    reactGridReady(reactGrid: SlickgridReactInstance) {
        this.setState({ reactGrid });
    }

    defineGrid() {

        const polygonFormatter = (_row: number, _cell: number, value: Polygon, _columnDef: Column, _dataContext: any) => {

            const coordinates = value.coordinates[0];
            // Find min and max coordinates for scaling
            const xCoords = coordinates.map((coord: Position) => coord[0]);
            const yCoords = coordinates.map((coord: Position) => coord[1]);
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

        const centroidXFormatter = (_row: number, _cell: number, value: Point, _columnDef: Column, _dataContext: any): string => {
            return value.coordinates[0].toString();
        }

        const centroidYFormatter = (_row: number, _cell: number, value: Point, _columnDef: Column, _dataContext: any): string => {
            return value.coordinates[1].toString();
        }

        const columns: Column[] = [
            { id: 'thumbnail', name: 'Thumbnail', field: 'parsedPolygon', sortable: true, minWidth: 100, formatter: polygonFormatter },
            { id: 'area', name: 'Area', field: 'area', sortable: true, minWidth: 100 },
            { id: 'centroidX', name: 'CentroidX', field: 'parsedCentroid', sortable: true, minWidth: 100, formatter: centroidXFormatter },
            { id: 'centroidY', name: 'CentroidY', field: 'parsedCentroid', sortable: true, minWidth: 100, formatter: centroidYFormatter },
            { id: 'class', name: 'Class', field: 'annotation_class_id', sortable: true, minWidth: 100 },
        ];

        const gridOptions: GridOption = {
            enableAutoResize: true,
            autoResize: {
                container: '#' + this.props.containerId,
                maxHeight: 200,
                minWidth: 10,
            },
            enableCellNavigation: true,
            enableRowSelection: true,
            multiSelect: false,

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

