import * as React from 'react';
import {Column, GridOption, SlickgridReactInstance, SlickgridReact} from "slickgrid-react";
import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';
import Annotation from "../types/annotations.ts";
import Image from "../types/image.ts";

interface Props {
    annotations: Annotation[];
    containerId: string;
}

export default class AnnotationList extends React.Component {
    constructor(public props: Props){
        super(props);

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
        if (prevProps.annotations !== this.props.annotations) {
            this.setState(() => ({
                ...this.state,
                dataset: this.getData(this.props.annotations),
            }));
        }
    }

    reactGridReady(reactGrid: SlickgridReactInstance) {
        this.reactGrid = reactGrid;
    }

    defineGrid() {
        const columns: Column[] = [
            { id: 'thumbnail', name: 'Thumbnail', field: 'thumbnail', sortable: true, minWidth: 100 },
            { id: 'area', name: 'Area', field: 'area', sortable: true, minWidth: 100 },
            { id: 'centroid', name: 'Centroid', field: 'centroid', sortable: true, minWidth: 100 },
            { id: 'class', name: 'Class', field: 'class', sortable: true, minWidth: 100 },
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

    getData(anns: Annotation[]) {
        const mappedData = anns.map((ann) => {
            return {
                id: ann.id,
                thumbnail: ann.custom_metrics.toString(),
                area: ann.area,
                centroid: ann.centroid.toString()
            };
        });

        return mappedData;
    }

    render() {
        return !this.state.gridOptions ? '' : (
            <SlickgridReact gridId={this.props.containerId + '-grid'}
                            columnDefinitions={this.state.columnDefinitions}
                            gridOptions={this.state.gridOptions}
                            dataset={this.state.dataset}
                            onReactGridCreated={$event => this.reactGridReady($event.detail)}
            />
        );
    }
}

