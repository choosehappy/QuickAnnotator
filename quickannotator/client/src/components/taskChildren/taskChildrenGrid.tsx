import * as React from 'react';
import { Column, GridOption, SlickgridReactInstance, SlickgridReact } from 'slickgrid-react';
import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';
import { getChildRayTasks } from '../../helpers/api.ts';
import { POLLING_INTERVAL_MS, TASK_STATE, TASK_STATE_MAP } from '../../helpers/config.ts';
import Button from 'react-bootstrap/Button';
import Collapse from 'react-bootstrap/Collapse';
import { SlickCustomTooltip } from '@slickgrid-universal/custom-tooltip-plugin';
import './taskChildrenGrid.css';


type TaskRow = {
    id: string; // unique id for SlickGrid
    task_id: string;
    func_or_class_name: string;
    state: string;
    creation_time_ms: number | null;
    end_time_ms: number | null;
    actor_progress: number;
    error_message: string | null;
};

interface Props {
    parentTaskId: string;
    containerId?: string;
}

type State = {
    gridOptions?: GridOption;
    columnDefinitions: Column[];
    dataset: TaskRow[];
    reactGrid?: SlickgridReactInstance | undefined;
    isExpanded: boolean;
};

export default class TaskChildrenGrid extends React.Component<Props, State> {
    gridRef: React.RefObject<SlickgridReact>;
    pollRef: number | null;

    constructor(props: Props) {
        super(props);
        this.gridRef = React.createRef<SlickgridReact>();
        this.pollRef = null;

        this.state = {
            gridOptions: undefined,
            columnDefinitions: [],
            dataset: [],
            reactGrid: undefined,
            isExpanded: false,
        };

        this.defineGrid = this.defineGrid.bind(this);
        this.reactGridReady = this.reactGridReady.bind(this);
        this.fetchChildrenOnce = this.fetchChildrenOnce.bind(this);
        this.startPolling = this.startPolling.bind(this);
        this.stopPolling = this.stopPolling.bind(this);
        this.toggleExpanded = this.toggleExpanded.bind(this);
    }

    componentDidMount() {
        this.defineGrid();
    }

    componentWillUnmount() {
        this.stopPolling();
    }

    componentDidUpdate(prevProps: Props, prevState: State) {
        const parentChanged = prevProps.parentTaskId !== this.props.parentTaskId;
        const expandedChanged = prevState.isExpanded !== this.state.isExpanded;

        if (expandedChanged || parentChanged) {
            if (this.state.isExpanded) {
                // If parent changed and we are expanded, restart polling
                this.startPolling();

                // wait for Collapse animation then resize grid
                setTimeout(() => {
                    this.state.reactGrid?.slickGrid.resizeCanvas();
                    this.state.reactGrid?.slickGrid.autosizeColumns();
                }, 50);
            } else {
                this.stopPolling();
            }
        }
    }

    defineGrid() {
        // Formatter for three explicit states: FINISHED, FAILED, PENDING
        // SlickGrid expects formatters to return strings/HTML; return an HTML string using inline SVG + Bootstrap spinner markup.
        const stateFormatter = (_row: number, _cell: number, value: string, _columnDef: Column, dataContext: TaskRow) => {
            const s = (value ?? '').toString().toUpperCase() as TASK_STATE;

            if (TASK_STATE_MAP[s]) {
                {
                    const raw = dataContext?.error_message ?? '';
                    const escapeHtml = (str: string) =>
                        String(str)
                            .replace(/&/g, '&amp;')
                            .replace(/</g, '&lt;')
                            .replace(/>/g, '&gt;')
                            .replace(/"/g, '&quot;')
                            .replace(/'/g, '&#39;');
                    const escaped = escapeHtml(raw);

                    // Show the state label and the full, formatted error below it (preserve whitespace).
                    // Also put the full escaped error in the title attribute for a native tooltip.
                    return `<div title="${escaped}" style="display:flex;flex-direction:column;">
                                <span>${TASK_STATE_MAP[s]}</span>
                            </div>`;
                }
            }

            // Fall back: raw value from the row
            return `<div style="display:flex;flex-direction:column;"><span>${TASK_STATE_MAP.SUBMITTED_TO_WORKER}</span></div>`;
        };


        const columns: Column[] = [
                { id: 'state', 
                    name: 'State', 
                    field: 'state', 
                    sortable: true, 
                    minWidth: 40, 
                    formatter: stateFormatter,
                    // use the formatter's `title` attribute as the tooltip when available
                    customTooltip: {    
                        useRegularTooltip: true, useRegularTooltipFromCellTextOnly: true 
                    }},
                { id: 'func', name: 'Function/Class', field: 'func_or_class_name', sortable: true, minWidth: 60,
                    // show a regular tooltip based on the cell text for the function/class column
                    customTooltip: { 
                        useRegularTooltip: true, useRegularTooltipFromCellTextOnly: true 
                    } },
            // { id: 'error', name: 'Error', field: 'error_message', sortable: false, minWidth: 60 },
            // { id: 'task_id', name: 'Task ID', field: 'task_id', sortable: true, minWidth: 60 },
        ];

        const options: GridOption = {
            enableAutoResize: false,
            // force fit columns so they will shrink/expand to fill the parent width
            forceFitColumns: true,
            autoResize: {
                // autoResize will measure the provided container; use the outer container id
                container: `#${this.props.containerId}`,
                // match annotationList: limit height and allow both x/y scroll when needed
                maxHeight: 200,
                minWidth: 300,
            },
            enableCellNavigation: true,
            enableRowSelection: true,
            multiSelect: false,
            showColumnHeader: false,
            externalResources: [new SlickCustomTooltip() as any]
        };

        this.setState(() => ({
            ...this.state,
            columnDefinitions: columns,
            gridOptions: options,
            dataset: [],
        }));
    }

    reactGridReady(reactGrid: SlickgridReactInstance) {
        this.setState({ reactGrid });
    }

    async fetchChildrenOnce() {
        try {
            const res = await getChildRayTasks(this.props.parentTaskId);
            if (res.status === 200 && Array.isArray(res.data)) {
                const rows: TaskRow[] = res.data.map((t: any, index: number) => ({
                    id: String(index),
                    task_id: t.task_id,
                    func_or_class_name: t.func_or_class_name,
                    state: t.state,
                    error_message: t.error_message ?? null,
                    creation_time_ms: t.creation_time_ms ?? null,
                    end_time_ms: t.end_time_ms ?? null,
                    actor_progress: t.actor_progress ?? 0,
                }));

                // Only update dataset
                this.state.reactGrid?.gridService.resetGrid();
                this.setState(() => ({
                    ...this.state,
                    dataset: rows,
                }));
            }
        } catch (err) {
            // swallow network or parsing errors for now; could surface later
            // console.error('fetchChildrenOnce error', err);
        }
    }

    startPolling() {
        // fetch immediately
        this.fetchChildrenOnce();
        // then poll
        this.pollRef = window.setInterval(() => {
            this.fetchChildrenOnce();
        }, POLLING_INTERVAL_MS) as unknown as number;
    }

    stopPolling() {
        if (this.pollRef) {
            clearInterval(this.pollRef as unknown as number);
            this.pollRef = null;
        }
    }

    toggleExpanded() {
        this.setState((s) => ({ ...s, isExpanded: !s.isExpanded }));
    }

    render() {
        if (!this.state.gridOptions) return null;

        return (
            <div id={this.props.containerId} style={{ borderRadius: 8, width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 8px' }}>
                    <Button variant="link" size="sm" onClick={this.toggleExpanded}>
                        {this.state.isExpanded ? 'Hide ▴' : 'Show ▾'}
                    </Button>
                </div>
                <Collapse in={this.state.isExpanded}>
                    <div>
                        <div style={{ width: '100%' }}>
                            <SlickgridReact ref={this.gridRef} gridId={`${this.props.containerId}-grid`}
                            columnDefinitions={this.state.columnDefinitions}
                            gridOptions={this.state.gridOptions}
                            dataset={this.state.dataset}
                            onReactGridCreated={$event => this.reactGridReady($event.detail)}
                            />
                        </div>
                    </div>
                </Collapse>
            </div>
        );
    }
}