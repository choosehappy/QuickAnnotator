import Card from 'react-bootstrap/Card';
import { useState } from "react";
import { Button, ListGroup, Modal, Spinner } from "react-bootstrap";
import { AnnotationClass, DLActorStatus, Image } from "../types.ts";
import { Plus, Pencil, Trash } from 'react-bootstrap-icons';
import { MODAL_DATA, MASK_CLASS_ID } from '../helpers/config.tsx';
import TrainingStatusButton from './TrainingStatusButton';
import { fetchAnnotationCounts, generateTissueMask } from '../helpers/api.ts';


interface Props {
    currentAnnotationClass: AnnotationClass | null;
    setcurrentAnnotationClass: (currentAnnotationClass: AnnotationClass) => void;
    setActiveModal: (activeModal: number | null) => void;
    annotationClasses: AnnotationClass[];
    setAnnotationClasses: (classes: AnnotationClass[]) => void;
    currentDlActorStatus: DLActorStatus | null;
    setCurrentDlActorStatus: (status: DLActorStatus | null) => void;
    currentImage: Image;
}

const ClassesPane = (props: Props) => {
    const [showMaskModal, setShowMaskModal] = useState(false);
    const [pendingClass, setPendingClass] = useState<AnnotationClass | null>(null);
    const [generating, setGenerating] = useState(false);

    const handleClassClick = async (c: AnnotationClass) => {
        // If clicking on the already-selected class, do nothing
        if (props.currentAnnotationClass?.id === c.id) return;

        // Only check mask when switching away from the tissue mask class
        if (props.currentAnnotationClass?.id === MASK_CLASS_ID && c.id !== MASK_CLASS_ID) {
            const resp = await fetchAnnotationCounts({ image_id: props.currentImage.id, annotation_class_id: MASK_CLASS_ID });
            const maskCount = resp.data?.[0]?.gt_count ?? 0;
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
                                                <>
                                                    <TrainingStatusButton
                                                        currentDlActorStatus={props.currentDlActorStatus}
                                                        setCurrentDlActorStatus={props.setCurrentDlActorStatus}
                                                        annotationClassId={c.id}
                                                    />
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
                                                </>
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
                    A tissue mask must be added before you can begin labeling with another class. Please select one of the two options:
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