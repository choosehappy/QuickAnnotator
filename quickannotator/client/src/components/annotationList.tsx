import * as React from 'react';
import {Column, GridOption, SlickgridReactInstance, SlickgridReact} from "slickgrid-react";
import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';


export default class AnnotationList extends React.Component {
    constructor(public props: any){
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
            dataset: this.getData(),
        }));

    }

    getData() {
        return [{
            id: 1,
            thumbnail: "placeholder",
            area: 1,
            centroid: "placeholder",
            class: "placeholder",
        }];
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

