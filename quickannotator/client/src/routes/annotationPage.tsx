import Container from 'react-bootstrap/Container'
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Stack from 'react-bootstrap/Stack';
import ClassesPane from "../components/classesPane.tsx";
import GroundTruthPane from "../components/groundTruthPane.tsx";
import PredictionsPane from "../components/predictionsPane.tsx";
import ViewportMap from "../components/viewportMap.tsx";
import ConfirmationModal from '../components/confirmationModal.tsx';
import React, { useState, useEffect, useRef } from 'react';
import { useOutletContext, useParams } from 'react-router-dom';

import { fetchImage, fetchProject, postAnnotations, startProcessingAnnotationClass, fetchAnnotationClasses, fetchAnnotationClassById, createAnnotationClass, deleteAnnotationClass } from "../helpers/api.ts";
import { DEFAULT_CLASS_ID, MODAL_DATA, TOOLBAR_KEYS } from '../helpers/config.ts';
import Card from "react-bootstrap/Card";
import Toolbar from "../components/toolbar.tsx";
import NewClassModal from '../components/newClassModal.tsx';
import { Annotation, AnnotationClass, OutletContextType, CurrentAnnotation, DataItem, IdNameElement } from "../types.ts";
import AnnotationExportModal from '../components/annotationExportModal.tsx';

function usePrevious<T>(value: T): T | undefined {
    const ref = useRef<T>();
    useEffect(() => {
        ref.current = value;
    }, [value]);
    return ref.current;
}

const AnnotationPage = () => {
    const { projectid, imageid } = useParams();
    const { currentImage, setCurrentImage, currentProject, setCurrentProject } = useOutletContext<OutletContextType>();

    const [currentAnnotationClass, setCurrentAnnotationClass] = useState<AnnotationClass | null>(null);
    const [gts, setGts] = useState<Annotation[]>([]);
    const [preds, setPreds] = useState<Annotation[]>([]);
    const [currentTool, setCurrentTool] = useState<string | null>('0');
    const [action, setAction] = useState<string | null>(null);
    const [currentAnnotation, setCurrentAnnotation] = useState<CurrentAnnotation | null>(null);
    const [highlightedPreds, setHighlightedPreds] = useState<Annotation[] | null>(null); // TODO: should just be a list of annotations
    const prevCurrentAnnotation = usePrevious<CurrentAnnotation | null>(currentAnnotation);
    const [activeModal, setActiveModal] = useState<number | null>(null);
    const [annotationClasses, setAnnotationClasses] = useState<AnnotationClass[]>([]);

    function handleConfirmImport() {
        // Set activeModal to null
        setActiveModal(null);

        // POST new annotations as ground truth
        // if (!highlightedPreds) return;
        postAnnotations(currentImage.id, currentAnnotationClass?.id, highlightedPreds?.map(ann => ann.parsedPolygon)).then((resp) => {
            setHighlightedPreds(null);
            setCurrentTool(TOOLBAR_KEYS.POINTER);
        });

    }

    function handleCancelImport() {
        setActiveModal(null);
        setHighlightedPreds(null);
        setCurrentTool(TOOLBAR_KEYS.POINTER);
    }

    async function handleDeleteClass() {
        const deleteResp = await deleteAnnotationClass(currentAnnotationClass?.id)
        if (deleteResp.status !== 204) {
            console.error("Error deleting annotation class:", deleteResp);
            return;
        }
        const getResp = await fetchAnnotationClasses();
        if (getResp.status !== 200) {
            console.error("Error fetching annotation classes:", getResp);
            return;
        }
        setAnnotationClasses(getResp.data);
        const newCurrentAnnotation = getResp.data.find((c) => c.id === DEFAULT_CLASS_ID);
        if (!newCurrentAnnotation) {
            console.error("Error: Default annotation class not found");
            return;
        }
        setCurrentAnnotationClass(newCurrentAnnotation);  // Assumed to be the tissue mask class
        setActiveModal(null);
    }

    function handleCancelDeleteClass() {
        setActiveModal(null);
    }


    function handleCancelExport() {
        setActiveModal(null);
    }

    useEffect(() => {
        if (projectid && imageid) {
            fetchProject(parseInt(projectid)).then((resp) => {
                setCurrentProject(resp.data);
            });
    
            fetchImage(parseInt(imageid)).then((resp) => {
                setCurrentImage(resp.data);
            });
        }

        fetchAnnotationClasses().then((resp) => {
            setAnnotationClasses(resp.data);
            setCurrentAnnotationClass(resp.data[DEFAULT_CLASS_ID - 1]);
        });
        
    }, [])

    useEffect(() => {
        if (!currentAnnotationClass) return;
        startProcessingAnnotationClass(currentAnnotationClass?.id).then((resp) => {
            if (resp.status === 200) {
                console.log("Processing started");
            }
        });
    }
    , [currentAnnotationClass]);

    useEffect(() => {
        fetchAnnotationClasses().then((resp) => {
            setAnnotationClasses(resp.data);
        });
    }, []);

    if (currentImage) {
        return (
            <>
                <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                    <ConfirmationModal activeModal={activeModal} config={MODAL_DATA.IMPORT_CONF} onConfirm={handleConfirmImport} onCancel={handleCancelImport}/>
                    <NewClassModal activeModal={activeModal} setActiveModal={setActiveModal} config={MODAL_DATA.ADD_CLASS} currentProject={currentProject} annotationClasses={annotationClasses} setAnnotationClasses={setAnnotationClasses}/>
                    <ConfirmationModal activeModal={activeModal} config={MODAL_DATA.DELETE_CLASS} onConfirm={handleDeleteClass} onCancel={handleCancelDeleteClass}/>
                    {currentAnnotationClass && (
                        <AnnotationExportModal 
                            show={activeModal === MODAL_DATA.EXPORT_CONF.id} 
                            setActiveModal={setActiveModal} 
                            images={[currentImage].map((item: IdNameElement) => new DataItem(item))} 
                            annotationClasses={annotationClasses.map((item: IdNameElement) => new DataItem(item))} // TODO: the annotation classes PR should raise the classes state up to the annotationPage
                        />
                    )}
                    <Row className="d-flex flex-grow-1">
                        <Col className="d-flex flex-grow-1">
                            <Card className="flex-grow-1">
                                <Card.Header style={{
                                    position: "absolute",
                                    top: 10,
                                    left: "50%",
                                    transform: "translate(-50%, 0%)",
                                    backgroundColor: "rgba(255, 255, 255, 0.6)",
                                    borderColor: "rgba(0, 0, 0, 0.8)",
                                    borderRadius: 6,
                                    zIndex: 10,
                                }}><Toolbar {...{ currentTool, 
                                                setCurrentTool, 
                                                action, 
                                                setAction }} /></Card.Header>
                                <Card.Body style={{ padding: "0px" }}>
                                    <ViewportMap {...{ currentImage, 
                                                    currentAnnotationClass, 
                                                    gts, 
                                                    setGts, 
                                                    preds, 
                                                    setPreds, 
                                                    currentTool, 
                                                    setCurrentTool,
                                                    currentAnnotation, 
                                                    setCurrentAnnotation, 
                                                    prevCurrentAnnotation,
                                                    highlightedPreds,
                                                    setHighlightedPreds,
                                                    activeModal,
                                                    setActiveModal
                                                    }} />
                                </Card.Body>
                            </Card>
                        </Col>
                        <Col xs={3}>
                            <Stack gap={3}>
                                <ClassesPane
                                    {...{ currentAnnotationClass, setcurrentAnnotationClass: setCurrentAnnotationClass, setActiveModal, annotationClasses, setAnnotationClasses }}
                                />
                                <GroundTruthPane
                                    {...{ gts, setGts, currentAnnotation, setCurrentAnnotation, annotationClasses, setActiveModal }}
                                />
                                <PredictionsPane
                                    {...{ preds, setPreds, currentAnnotation, annotationClasses }}
                                />
                            </Stack>
                        </Col>
                    </Row>
                </Container>
            </>
        )
    }
};

export default AnnotationPage