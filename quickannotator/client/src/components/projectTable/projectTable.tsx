import * as React from 'react';
import { Column, GridOption, SlickgridReactInstance, SlickgridReact } from "slickgrid-react";
import { Modal, Container, Row, Col, Card, ButtonToolbar, ButtonGroup, Button, ListGroup, Nav } from "react-bootstrap";

import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';
import { Project } from "../../types.ts";
import { Link } from 'react-router-dom';

interface Props {
    projects: Project[];
    containerId: string;
    deleteHandle: (project: any) => void;
    editHandle: (project: any) => void;
}

export default class ProjectTable extends React.PureComponent {
    constructor(public props: Props) {
        super(props);
        this.gridRef = React.createRef();
        this.state = {
            gridOptions: undefined,
            columnDefinitions: [],
            dataset: [],
            reactGrid: undefined,
            // deletedImageId: undefined,
            // deletedImageName: undefined,
            // confirmShow: false
        };
        this.clickOnDelete = this.clickOnDelete.bind(this);
        this.handleClose = this.handleClose.bind(this);
    }

    componentDidMount() {
        // define the grid options & columns and then create the grid itself
        this.defineGrid();
    }

    clickOnDelete(data: any) {
        console.log('deleted', data.id)
        this.setState({ ...this.state, confirmShow: true, deletedImageId: data.id, deletedImageName: data.name })

    }

    componentDidUpdate(prevProps: Props) {
        if (prevProps.projects !== this.props.projects) {
            this.state.reactGrid?.gridService.resetGrid();
            this.setState(() => ({
                ...this.state,
                dataset: this.props.projects,
            }));
        }
    }

    handleClose() {
        this.setState({ ...this.state, confirmShow: false })
    }

    reactGridReady(reactGrid: SlickgridReactInstance) {
        this.setState({ reactGrid });
    }

    defineGrid() {
        const actionFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
            const delBtn = document.createElement('button');
            delBtn.className = 'btn btn-danger btn-sm project-icon';
            delBtn.textContent = 'delete'
            delBtn.addEventListener('click', (e) => { this.props.deleteHandle(dataContext) })

            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-primary btn-sm project-icon';
            editBtn.textContent = 'edit'
            // const editIcon = document.createElement('PencilSquare');
            // editBtn.appendChild(editIcon)
            editBtn.addEventListener('click', (e) => { this.props.editHandle(dataContext) })

            const div = document.createElement('div');
            div.appendChild(editBtn)
            div.appendChild(delBtn)
            return div
        }
        const nameFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {

            return `<a href="/project/${dataContext.id}">${value}</a>`
        }

        const columns: Column[] = [
            { id: 'id', name: 'Id', field: 'id', sortable: true },
            { id: 'name', name: 'Name', field: 'name', sortable: true, formatter: nameFormatter },
            { id: 'is_dataset_large', name: 'Large Dataset', field: 'is_dataset_large', sortable: true },
            { id: 'description', name: 'Description', field: 'description', sortable: true },
            { id: 'datetime', name: 'Date Time', field: 'datetime', sortable: true },
            { id: 'action', name: '', field: 'action', sortable: true, formatter: actionFormatter }
        ];

        const gridOptions: GridOption = {
            enableAutoResize: true,
            autoHeight: true,
            rowHeight: 64,
            resizeSensitivity: true,
            forceFitColumns: true,
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

    getData(projects: Project[]) {
        const mappedData = projects.map((proj) => {
            return {
                id: proj.id,
                name: proj.name,
                is_dataset_large: proj.is_dataset_large,
                datetime: proj.datetime
            };
        });

        return mappedData;
    }

    render() {
        return !this.state.gridOptions ? '' : (
            <>
                <div style={{ borderRadius: '8px', overflow: 'hidden' }}>
                    <SlickgridReact ref={this.gridRef} gridId={this.props.containerId + '-grid'}
                        columnDefinitions={this.state.columnDefinitions}
                        gridOptions={this.state.gridOptions}
                        dataset={this.state.dataset}
                        onReactGridCreated={$event => this.reactGridReady($event.detail)}
                    />
                </div>
            </>
        );
    }
}

