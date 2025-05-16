import * as React from 'react';
import { Column, GridOption, SlickgridReactInstance, SlickgridReact } from "slickgrid-react";
import { Modal, Container, Row, Col, Card, ButtonToolbar, ButtonGroup, Button, ListGroup } from "react-bootstrap";

import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';
import { Image, Project } from "../../types.ts";

interface Props {
    project: Project;
    images: Image[];
    changed: boolean;
    containerId: string;
    deleteHandler: (imageId: number)=>void;
}

export default class ImageTable extends React.PureComponent {
    constructor(public props: Props) {
        super(props);
        this.gridRef = React.createRef();
        this.state = {
            gridOptions: undefined,
            columnDefinitions: [],
            dataset: [],
            reactGrid: undefined,
            deletedImageId: undefined,
            deletedImageName: undefined,
            confirmShow: false
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
        this.setState({...this.state, confirmShow: true, deletedImageId: data.id, deletedImageName: data.name})
        
    }
    
    componentDidUpdate(prevProps: Props, prevStates) {
        if (prevProps.images !== this.props.images) {
            this.state.reactGrid?.gridService.resetGrid();
            this.setState(() => ({
                ...this.state,
                dataset: this.getData(this.props.images),
            }));
        }
        if (prevProps.changed !== this.props.changed) {
            this?.gridRef?.current?.resizerService?.resizeGrid(5);
        }


    }

    handleClose() {
        this.setState({...this.state, confirmShow: false})
    }

    reactGridReady(reactGrid: SlickgridReactInstance) {
        this.setState({ reactGrid });
    }

    defineGrid() {
        console.log('defineGrid',this.props)
        const thumbnailFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {

            return `<a target="_blank" href="../project/${this.props.project.id}/annotate/${value}"><img src='../api/v1/image/${value}/1/file' height='64'></img></a>`
        }
        const actionFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
            console.log(dataContext)
            const delBtn = document.createElement('button')
            delBtn.classList.add('btn')
            delBtn.classList.add('btn-danger')
            delBtn.classList.add('btn-sm')
            delBtn.textContent = 'delete'
            delBtn.addEventListener('click', ()=>{this.clickOnDelete(dataContext)})
            return delBtn
        }
        const columns: Column[] = [
            { id: 'thumbnail', name: '', field: 'id', sortable: true, formatter: thumbnailFormatter },
            { id: 'id', name: 'Id', field: 'id', sortable: true },
            { id: 'name', name: 'Name', field: 'name', sortable: true },
            { id: 'width', name: 'Width', field: 'width', sortable: true },
            { id: 'height', name: 'Height', field: 'height', sortable: true },
            { id: 'dz_tilesize', name: 'DZ Tile Size', field: 'dz_tilesize', sortable: true },
            { id: 'date', name: 'Date', field: 'date', sortable: true },
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

    getData(images: Image[]) {
        const mappedData = images.map((img) => {
            return {
                id: img.id,
                name: img.name,
                width: img.base_width,
                height: img.base_height,
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
            <>
                <Modal show={this.state.confirmShow} onHide={this.handleClose}>
                    <Modal.Header closeButton>
                        <Modal.Title>Modal heading</Modal.Title>
                    </Modal.Header>
                    <Modal.Body>Do you sure you want to delete <strong>{this.state.deletedImageId}: {this.state.deletedImageName}</strong></Modal.Body>
                    <Modal.Footer>
                        <Button variant="secondary" onClick={this.handleClose}>
                            Cancel
                        </Button>
                        <Button variant="danger" onClick={()=>{
                                
                                this.props.deleteHandler(this.state.deletedImageId)
                                this.setState({...this.state, confirmShow: false})
                            }}>
                            Delete
                        </Button>
                    </Modal.Footer>
                </Modal>
                <SlickgridReact ref={this.gridRef} gridId={this.props.containerId + '-grid'}
                    columnDefinitions={this.state.columnDefinitions}
                    gridOptions={this.state.gridOptions}
                    dataset={this.state.dataset}
                    onReactGridCreated={$event => this.reactGridReady($event.detail)}
                />
            </>
        );
    }
}

