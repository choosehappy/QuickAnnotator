import Card from 'react-bootstrap/Card';
import { useState, useRef } from "react";
import { Button, ListGroup, Modal, Spinner } from "react-bootstrap";
import { AnnotationClass, DLActorStatus, Image, Project } from "../types.ts";
import { Plus, Pencil, Trash } from 'react-bootstrap-icons';
import { MODAL_DATA, MASK_CLASS_ID } from '../helpers/config.tsx';
import TrainingStatusButton from './TrainingStatusButton';
import { fetchProjectAnnotationStats, generateTissueMask, setInferenceThreshold } from '../helpers/api.ts';


interface Props {
    currentAnnotationClass: AnnotationClass | null;
    setcurrentAnnotationClass: (currentAnnotationClass: AnnotationClass) => void;
    setActiveModal: (activeModal: number | null) => void;
    annotationClasses: AnnotationClass[];
    setAnnotationClasses: (classes: AnnotationClass[]) => void;
    currentDlActorStatus: DLActorStatus | null;
    setCurrentDlActorStatus: (status: DLActorStatus | null) => void;
    currentImage: Image;
    currentProject: Project;
    inferenceThreshold: number | null;
    setInferenceThreshold: (threshold: number | null) => void;
    onStatusRefresh?: (status: DLActorStatus) => void;
}

const ClassesPane = (props: Props) => {
    const [showMaskModal, setShowMaskModal] = useState(false);
    const [pendingClass, setPendingClass] = useState<AnnotationClass | null>(null);
    const [generating, setGenerating] = useState(false);
    const [showSlider, setShowSlider] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [sliderValue, setSliderValue] = useState(0.5);
    const sliderRef = useRef<HTMLDivElement>(null);

    const handleSaveThreshold = async (value: number) => {
        if (!props.currentAnnotationClass) return;
        setIsSaving(true);
        try {
            const response = await setInferenceThreshold(props.currentAnnotationClass.id, value);
            if (response.status === 200) {
                props.setInferenceThreshold(response.data.inference_threshold);
                if (props.onStatusRefresh) {
                    props.onStatusRefresh(response.data);
                }
            }
        } finally {
            setIsSaving(false);
        }
    };

    const handleClassClick = async (c: AnnotationClass) => {
        // If clicking on the already-selected class, do nothing
        if (props.currentAnnotationClass?.id === c.id) return;

        // Only check mask when switching away from the tissue mask class
        if (props.currentAnnotationClass?.id === MASK_CLASS_ID && c.id !== MASK_CLASS_ID) {
            const resp = await fetchProjectAnnotationStats(props.currentProject.id, 'annotation_class', [MASK_CLASS_ID], [props.currentImage.id]);
            const maskCount = resp.data?.[0]?.stats.count ?? 0;
            if (maskCount > 0) {
                // Mask exists, proceed with class switch
                props.setcurrentAnnotationClass(c);
                props.setCurrentDlActorStatus(null);
            } else {
                // No mask — show modal
                setPendingClass(c);
                setShowMaskModal(true);
            }
            return;
        }

        props.setcurrentAnnotationClass(c);
        props.setCurrentDlActorStatus(null);
    };

    const handleAddOwnMask = () => {
        // Cancel — stay on tissue mask class
        setShowMaskModal(false);
        setPendingClass(null);
    };

    const handleAutoGenerate = async () => {
        setGenerating(true);
        try {
            const resp = await generateTissueMask(props.currentImage.id);
            if (resp.status === 200) {
                setShowMaskModal(false);
                // Re-select tissue mask class to trigger viewport re-render with generated polygons.
                // Spread to create a new object reference so React detects the change.
                const maskClass = props.annotationClasses.find(c => c.id === MASK_CLASS_ID);
                if (maskClass) {
                    props.setcurrentAnnotationClass({...maskClass});
                }
                setPendingClass(null);
            }
        } finally {
            setGenerating(false);
        }
    };

    return (
        <>
            <Card>
                <Card.Header as={'h5'} className='d-flex justify-content-between align-items-center'>
                    Annotation Classes
                    <Button variant="secondary" className='btn btn-primary btn-sm'>
                        <Plus onClick={() => props.setActiveModal(MODAL_DATA.ADD_CLASS.id)}/>
                    </Button>
                </Card.Header>
                <Card.Body>
                    {props.currentAnnotationClass && props.currentAnnotationClass.id !== MASK_CLASS_ID && (
                        <div className="d-flex align-items-center mb-3">
                            <TrainingStatusButton
                                currentDlActorStatus={props.currentDlActorStatus}
                                setCurrentDlActorStatus={props.setCurrentDlActorStatus}
                                annotationClassId={props.currentAnnotationClass.id}
                            />
                            <div 
                                ref={sliderRef}
                                onMouseEnter={() => {
                                    setShowSlider(true);
                                    setSliderValue(props.inferenceThreshold ?? 0.5);
                                }}
                                onMouseLeave={() => {
                                    setShowSlider(false);
                                    if (props.inferenceThreshold !== null && Math.abs(sliderValue - props.inferenceThreshold) > 0.001) {
                                        handleSaveThreshold(sliderValue);
                                    }
                                }}
                                className="ms-1 btn btn-outline-secondary btn-sm"
                                style={{ 
                                    position: 'relative', 
                                    overflow: 'hidden',
                                    height: 31,
                                    width: showSlider && props.inferenceThreshold !== null ? 220 : 190,
                                    transition: 'width 0.25s ease',
                                    padding: '0 0.5rem',
                                    fontSize: '0.8rem',
                                    cursor: props.inferenceThreshold === null ? 'default' : 'pointer',
                                    opacity: props.inferenceThreshold === null ? 0.65 : 1,
                                }}
                            >
                                {/* Label / value display */}
                                <div 
                                    style={{ 
                                        position: 'absolute',
                                        top: 0,
                                        bottom: 0,
                                        left: 8,
                                        right: 8,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        gap: 6,
                                        whiteSpace: 'nowrap',
                                        lineHeight: 1,
                                        opacity: showSlider && props.inferenceThreshold !== null ? 0 : 1,
                                        transition: 'opacity 0.2s ease',
                                        pointerEvents: 'none',
                                    }}
                                >
                                    {isSaving ? (
                                        <Spinner animation="border" style={{ width: '1rem', height: '1rem' }} />
                                    ) : (
                                        <>
                                            <span>Inference Threshold:</span>
                                            <span>{props.inferenceThreshold?.toFixed(2) ?? '—'}</span>
                                        </>
                                    )}
                                </div>

                                {/* Slider control */}
                                <div
                                    style={{
                                        position: 'absolute',
                                        top: 0,
                                        bottom: 0,
                                        left: 8,
                                        right: 8,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 6,
                                        opacity: showSlider && props.inferenceThreshold !== null ? 1 : 0,
                                        transition: 'opacity 0.25s ease 0.1s',
                                        pointerEvents: showSlider ? 'auto' : 'none',
                                    }}
                                >
                                    <input 
                                        type="range" 
                                        min="0.01" 
                                        max="0.99" 
                                        step="0.01" 
                                        value={sliderValue}
                                        onChange={(e) => setSliderValue(parseFloat(e.target.value))}
                                        onClick={(e) => e.stopPropagation()}
                                        style={{ flex: 1 }}
                                    />
                                    <span style={{ minWidth: 32, textAlign: 'right' }}>{sliderValue.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>
                    )}
                    <ListGroup 
                        defaultActiveKey={props.currentAnnotationClass?.id} 
                        style={{ maxHeight: '300px', overflowY: 'auto' }}
                    >
                        {props.annotationClasses.map((c) => {
                                return (
                                    <ListGroup.Item 
                                        key={c.id}
                                        action 
                                        onClick={() => handleClassClick(c)}
                                        active={props.currentAnnotationClass?.id === c.id}
                                        className="d-flex justify-content-between align-items-center list-group-item-secondary"
                                    >
                                        <span>{c.name}</span>
                                        <div className="d-flex align-items-center">
                                            {c.id !== MASK_CLASS_ID && c.id === props.currentAnnotationClass?.id && (
                                                <Button 
                                                    variant="outline-danger" 
                                                    size="sm"
                                                    className="ms-2"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        props.setActiveModal(MODAL_DATA.DELETE_CLASS.id);
                                                    }}
                                                >
                                                    <Trash />
                                                </Button>
                                            )}
                                            <Button 
                                                disabled 
                                                size="lg" 
                                                style={{ backgroundColor: c.color, border: 'none' }}
                                                className="ms-2"
                                            >
                                            </Button>
                                        </div>
                                    </ListGroup.Item>
                                )
                            }
                        )}
                    </ListGroup>
                </Card.Body>
            </Card>

            <Modal show={showMaskModal} onHide={handleAddOwnMask} centered>
                <Modal.Header closeButton>
                    <Modal.Title>Tissue Mask Required</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    A tissue mask must be added before you can switch to another annotation class. Please select one of the two options:
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={handleAddOwnMask} disabled={generating}>
                        Add my own tissue mask
                    </Button>
                    <Button variant="primary" onClick={handleAutoGenerate} disabled={generating}>
                        {generating ? (
                            <>
                                <Spinner animation="border" size="sm" className="me-2" />
                                Generating...
                            </>
                        ) : (
                            'Auto-generate tissue mask'
                        )}
                    </Button>
                </Modal.Footer>
            </Modal>
        </>
    )
}

export default ClassesPane;