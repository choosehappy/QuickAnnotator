import { useEffect, useRef, useState } from 'react';
import { Column, GridOption, SlickgridReactInstance, SlickgridReact } from 'slickgrid-react';
import '@slickgrid-universal/common/dist/styles/css/slickgrid-theme-bootstrap.css';
import { listRayTasks } from '../../helpers/api.ts';
import { POLLING_INTERVAL_MS } from '../../helpers/config.ts';
import Button from 'react-bootstrap/Button';
import Collapse from 'react-bootstrap/Collapse';

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

const TaskChildrenGrid = (props: Props) => {
    const gridRef = useRef<SlickgridReact | null>(null);
    const reactGrid = useRef<SlickgridReactInstance | undefined>(undefined);
    const [gridOptions, setGridOptions] = useState<GridOption | undefined>(undefined);
    const [columnDefinitions, setColumnDefinitions] = useState<Column[]>([]);
    const [dataset, setDataset] = useState<TaskRow[]>([]);
    const [isExpanded, setIsExpanded] = useState<boolean>(false);
    const pollRef = useRef<number | null>(null);

    useEffect(() => {
        defineGrid();
        return () => {
            if (pollRef.current) {
                clearInterval(pollRef.current as unknown as number);
                pollRef.current = null;
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // useEffect(() => {
    //     // when parentTaskId changes, reset dataset and restart polling
    //     setDataset([]);
    //     if (pollRef.current) {
    //         clearInterval(pollRef.current as unknown as number);
    //         pollRef.current = null;
    //     }
    //     startPolling();
    //     // eslint-disable-next-line react-hooks/exhaustive-deps
    // }, [props.parentTaskId]);

    function defineGrid() {
        const formatTimestamp = (ts: number | null) => {
            if (!ts) return '';
            try {
                return new Date(ts).toLocaleString();
            } catch (e) {
                return String(ts);
            }
        };
        const columns: Column[] = [
            { id: 'func', name: 'Function/Class', field: 'func_or_class_name', sortable: true, minWidth: 150 },
            { id: 'state', name: 'State', field: 'state', sortable: true, minWidth: 80 },
            { id: 'error', name: 'Error', field: 'error_message', sortable: false, minWidth: 200 },
        ];

        const options: GridOption = {
            enableAutoResize: true,
            forceFitColumns: true,
            autoResize: {
            container: `#${props.containerId}`,
            maxHeight: 400,
            },
            enableCellNavigation: true,
            enableRowSelection: true,
            multiSelect: false,
        };

        setColumnDefinitions(columns);
        setGridOptions(options);
    }

    function reactGridReadyHandler(event: CustomEvent) {
        reactGrid.current = event.detail as SlickgridReactInstance;
    }

    async function fetchChildrenOnce() {
        try {
            const res = await listRayTasks([{ parent_task_id: props.parentTaskId }]);
            if (res.status === 200 && Array.isArray(res.data)) {
                const rows: TaskRow[] = res.data.map((t: any) => ({
                    id: t.task_id ?? (t.id || Math.random().toString(36).slice(2)),
                    task_id: t.task_id,
                    func_or_class_name: t.func_or_class_name,
                    state: t.state,
                    creation_time_ms: t.creation_time_ms ?? null,
                    end_time_ms: t.end_time_ms ?? null,
                    actor_progress: t.actor_progress ?? 0,
                    error_message: t.error_message ?? null,
                }));

                // update dataset and reset grid so it re-renders
                setDataset(rows);
                reactGrid.current?.gridService.resetGrid();
            }
        } catch (err) {
            // eslint-disable-next-line no-console
            console.warn('Failed to fetch child tasks for', props.parentTaskId, err);
        }
    }

    function startPolling() {
        // fetch immediately
        fetchChildrenOnce();
        // then poll
        pollRef.current = window.setInterval(() => {
            fetchChildrenOnce();
        }, POLLING_INTERVAL_MS) as unknown as number;
    }

    function stopPolling() {
        if (pollRef.current) {
            clearInterval(pollRef.current as unknown as number);
            pollRef.current = null;
        }
    }

    // start/stop polling when expanded state changes or parent id changes
    useEffect(() => {
        if (isExpanded) {
            // start polling for the current parent
            startPolling();
        } else {
            stopPolling();
        }

        return () => {
            stopPolling();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isExpanded, props.parentTaskId]);

    return !gridOptions ? null : (
        <div id={props.containerId} style={{ borderRadius: 8, overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 8px' }}>
                <Button variant="link" size="sm" onClick={() => setIsExpanded((s) => !s)}>
                    {isExpanded ? 'Hide ▴' : 'Show ▾'}
                </Button>
            </div>
            <Collapse in={isExpanded}>
                <div>
                    <SlickgridReact ref={gridRef} gridId={`${props.containerId}-grid`}
                        columnDefinitions={columnDefinitions}
                        gridOptions={gridOptions}
                        dataset={dataset}
                        onReactGridCreated={$event => reactGridReadyHandler($event.detail)}
                    />
                </div>
            </Collapse>
        </div>
    );
}

export default TaskChildrenGrid;