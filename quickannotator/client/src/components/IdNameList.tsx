import * as React from 'react';
import {Column, GridOption, SlickgridReactInstance, SlickgridReact, } from "slickgrid-react";
import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';
import { DataItem, IdNameElement } from "../types.ts";

interface Props {
    items: DataItem[];
    containerId: string;
}

export default class IdNameList extends React.Component<Props, any> {
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

    toggleCompletedProperty(item: any) {    // https://github.com/ghiscoding/slickgrid-react/blob/master/src/examples/slickgrid/Example2.tsx
        // toggle property
        if (typeof item === 'object') {
          item.selected = !item.selected;
        this.state.reactGrid?.gridService.updateItemById(item.id, item, { highlightRow: false });
        }
    }


    reactGridReady(reactGrid: SlickgridReactInstance) {
        this.setState({ reactGrid });
    }

    checkboxFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
        const isChecked = dataContext.selected;
        return `<input type="checkbox" ${isChecked ? 'checked' : ''} />`;
    };


    defineGrid() {

        const columns: Column[] = [
            { 
                id: 'name', 
                name: 'name', 
                field: 'name', 
                sortable: true, 
                minWidth: 100 
            },
            { 
                id: 'selected', 
                name: 'selected', 
                field: 'selected', 
                formatter: this.checkboxFormatter, 
                minWidth: 30, 
                maxWidth: 100, 
                resizable: false, 
            },
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
            showHeaderRow: false, // Hide the header row
            showColumnHeader: false, // Hide the column names row
        };

        this.setState(() => ({
            ...this.state,
            columnDefinitions: columns,
            gridOptions,
            dataset: this.props.items,
        }));

    }

    render() {
        return !this.state.gridOptions ? '/' : (
            <SlickgridReact gridId={this.props.containerId + '-grid'}
                            columnDefinitions={this.state.columnDefinitions}
                            gridOptions={this.state.gridOptions}
                            dataset={this.state.dataset}
                            onReactGridCreated={$event => this.reactGridReady($event.detail)}
            />
        );
    }
}

