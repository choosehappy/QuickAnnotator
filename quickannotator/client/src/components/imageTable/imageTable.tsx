import * as React from 'react';
import { Column, GridOption, SlickgridReactInstance, SlickgridReact } from "slickgrid-react";
import { Editors } from "@slickgrid-universal/common";
import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';
import './imageTable.css';
import { AnnotationClass, Image, Project } from "../../types.ts";
import {getAnnotationPageURL, getImageThumbnailURL, updateImageComment } from "../../helpers/api.ts";
import ConfirmationModal from '../confirmationModal.tsx';
import { MODAL_DATA, COOKIE_NAMES } from '../../helpers/config.tsx';
interface Props {
    project: Project;
    images: Image[];
    annotationClasses: AnnotationClass[];
    annotationCounts: Record<number, Record<number, number>> | null;
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
            activeModal: null
        };
        this.clickOnDelete = this.clickOnDelete.bind(this);
        this.handleClose = this.handleClose.bind(this);
    }

    componentDidMount() {
        // define the grid options & columns and then create the grid itself
        this.defineGrid();
    }

    saveComment = async (imageId: number, comment: string) => {
        try {
            await updateImageComment(imageId, comment);
        } catch (err) {
            console.error('Failed to save image comment:', err);
        }
    }
    
    
    clickOnDelete(data: any) {
        console.log('deleted', data.id)
        this.setState({...this.state, activeModal: MODAL_DATA.DELETE_IMAGE.id, deletedImageId: data.id, deletedImageName: data.name})
        
    }
    
    componentDidUpdate(prevProps: Props, prevStates) {
        if (prevProps.annotationClasses !== this.props.annotationClasses) {
            const columns = this.buildColumns();
            const dataset = this.getData(this.props.images);
            this.setState(() => ({
                ...this.state,
                columnDefinitions: columns,
                dataset,
            }), () => {
                this.state.reactGrid?.slickGrid?.setColumns(columns);
            });
        } else if (prevProps.images !== this.props.images || prevProps.annotationCounts !== this.props.annotationCounts) {
            const dataset = this.getData(this.props.images);
            this.state.reactGrid?.gridService.resetGrid();
            this.setState(() => ({
                ...this.state,
                dataset,
            }));
        }
        if (prevProps.changed !== this.props.changed) {
            this?.gridRef?.current?.resizerService?.resizeGrid(5);
        }


    }

    handleClose() {
        this.setState({...this.state, activeModal: null})
    }

    reactGridReady(reactGrid: SlickgridReactInstance) {
        this.setState({ reactGrid });
        reactGrid.slickGrid?.onClick.subscribe((e, args) => {
            if ((e.target as HTMLElement).closest('button')) return;
            if (!args.grid || args.cell == null) return;

            const column = args.grid.getColumns()[args.cell];

            if (column?.id === 'comment') {
                console.log("comment column clicked");
                return;
            }

            const item = args.grid.getDataItem(args.row);
            if (!item || this.props.project?.id == null) return;
            window.location.href = `..${getAnnotationPageURL(this.props.project.id, item.id)}`;
        });

        
        reactGrid.slickGrid?.onCellChange.subscribe((e, args) => {
            const dataContext = args?.item;
            if (dataContext) {
                this.saveComment(dataContext.id, dataContext.comment || '');
            }
        });
    }

    defineGrid() {
        const columns = this.buildColumns();

        const gridOptions: GridOption = {
            enableAutoResize: true,
            rowHeight: 64,
            forceFitColumns: true,
            enableCellNavigation: true,
            autoResize: {
                container: `#${this.props.containerId}`,
                maxHeight: undefined,
            },
            editable: true,
        };

        this.setState(() => ({
            ...this.state,
            columnDefinitions: columns,
            gridOptions,
            dataset: [],
        }));
    }

    buildColumns(): Column[] {
        const thumbnailFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
            if (!this.props.project) {
                console.error('No project defined for image table thumbnail formatter')
                return ''
            }
            const src = `..${getImageThumbnailURL(value)}`;
            return `<span class="spinner-border spinner-border-sm" role="status"></span>` +
                `<span class="text-danger" style="display:none;font-size:1.5rem">&times;</span>` +
                `<img src='${src}' height='64' style='display:none'` +
                ` onload='this.previousElementSibling.previousElementSibling.style.display="none";this.style.display="block"'` +
                ` onerror='this.previousElementSibling.previousElementSibling.style.display="none";this.previousElementSibling.style.display="inline"'>`;
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

        const editor = {
            model: Editors.longText
        };
        
        return [
            { id: 'thumbnail', name: '', field: 'id', sortable: true, formatter: thumbnailFormatter },
            { id: 'id', name: 'Id', field: 'id', sortable: true },
            { id: 'name', name: 'Name', field: 'name', sortable: true },
            { id: 'width', name: 'Width', field: 'width', sortable: true },
            { id: 'height', name: 'Height', field: 'height', sortable: true },
            { id: 'dz_tilesize', name: 'DZ Tile Size', field: 'dz_tilesize', sortable: true },
            { id: 'date', name: 'Date', field: 'date', sortable: true },
            { id: 'comment', name: 'Comment', field: 'comment', sortable: true, editor: editor, type: 'string', editable: true },
            ...this.getAnnotationClassColumns(),
            { id: 'action', name: '', field: 'action', sortable: true, formatter: actionFormatter }
        ];
    }

    getAnnotationClassColumns(): Column[] {
        if (!this.props.annotationClasses || this.props.annotationClasses.length === 0) {
            return [];
        }
        const spinnerFormatter = (row: number, cell: number, value: any) => {
            if (value === null) {
                return '<span class="spinner-border spinner-border-sm" role="status"></span>';
            }
            return value;
        };
        return this.props.annotationClasses.map((ac) => ({
            id: `class_gt_${ac.id}`,
            name: `No. ${ac.name} (GT)`,
            field: `class_gt_${ac.id}`,
            sortable: true,
            type: 'number',
            formatter: spinnerFormatter,
        }));
    }

    getData(images: Image[]) {
        const annotationClasses = this.props.annotationClasses || [];
        const countsLoaded = this.props.annotationCounts !== null;
        const counts = this.props.annotationCounts || {};
        const mappedData = images.map((img) => {
            const row: any = {
                id: img.id,
                name: img.name,
                width: img.base_width,
                height: img.base_height,
                embeddingCoord: img.embeddingCoord,
                group_id: img.group_id,
                dz_tilesize: img.dz_tilesize,
                comment: img.comment || '',
                date: img.datetime,
            };
            const imgCounts = counts[img.id] || {};
            for (const ac of annotationClasses) {
                row[`class_gt_${ac.id}`] = countsLoaded ? (imgCounts[ac.id] ?? 0) : null;
            }
            return row;
        });

        return mappedData;
    }

    render() {
        return !this.state.gridOptions ? '' : (
            <>
                <ConfirmationModal
                    activeModal={this.state.activeModal}
                    config={MODAL_DATA.DELETE_IMAGE}
                    onConfirm={() => {
                        this.props.deleteHandler(this.state.deletedImageId);
                        this.setState({...this.state, activeModal: null});
                    }}
                    onCancel={this.handleClose}
                    checkboxCookieName={COOKIE_NAMES.SKIP_CONFIRM_DELETE_IMAGE}
                />
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

