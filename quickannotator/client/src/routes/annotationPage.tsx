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

import { fetchImage, fetchProject, postAnnotations, startProcessingAnnotationClass, searchAnnotationClasses, fetchAnnotationClassById, createAnnotationClass, deleteAnnotationClass } from "../helpers/api.ts";
import { DEFAULT_CLASS_ID, MODAL_DATA, TOOLBAR_KEYS, MASK_CLASS_ID, COOKIE_NAMES } from '../helpers/config.ts';
import Card from "react-bootstrap/Card";
import Toolbar from "../components/toolbar.tsx";
import Legend from '../components/legend.tsx';
import NewClassModal from '../components/newClassModal.tsx';
import { Annotation, AnnotationClass, OutletContextType, CurrentAnnotation, DataItem, IdNameElement } from "../types.ts";
import AnnotationExportModal from '../components/annotationExportModal.tsx';
import { propTypes } from 'react-bootstrap/esm/Image';
import { CookiesProvider } from 'react-cookie';
import { useHotkeys } from 'react-hotkeys-hook';

const AnnotationPage = () => {
    const { projectid, imageid } = useParams();
    const { currentImage, setCurrentImage, currentProject, setCurrentProject } = useOutletContext<OutletContextType>();

    const [currentAnnotationClass, setCurrentAnnotationClass] = useState<AnnotationClass | null>();
    const [gts, setGts] = useState<Annotation[]>([]);
    const [preds, setPreds] = useState<Annotation[]>([]);
    const [currentTool, setCurrentTool] = useState<string | null>('0');
    const [ctrlHeld, setCtrlHeld] = useState(false);
    const [currentAnnotation, setCurrentAnnotation] = useState<CurrentAnnotation | null>(null);
    const [highlightedPreds, setHighlightedPreds] = useState<Annotation[] | null>(null);
    const prevCurrentAnnotation = useRef<CurrentAnnotation | null>(null);
    const [activeModal, setActiveModal] = useState<number | null>(null);
    const [mouseCoords, setMouseCoords] = useState<{ x: number, y: number }>({x: 0, y: 0});
    const [annotationClasses, setAnnotationClasses] = useState<AnnotationClass[]>([]);

    function setCurrentAndPreviousAnnotation(newAnnotation: Annotation | null) {    // NOTE: Consider making this a custom hook if the pattern is used elsewhere
        setCurrentAnnotation((currAnn: CurrentAnnotation | null) => {
            const prevAnnotationId = currAnn?.currentState ?? null;
            const newAnnotationId = newAnnotation?.id ?? null;

            // If the user clicked away from an annotation update currentAnnotation to null
            if (newAnnotation === null) {
                prevCurrentAnnotation.current = currAnn;
                return null;
            }

            // If the user clicked on a different annotation, create a new CurrentAnnotation and save the last one to prevCurrentAnnotation
            if (newAnnotationId !== prevAnnotationId) {
                prevCurrentAnnotation.current = currAnn;
                return new CurrentAnnotation(newAnnotation);
            } else {
                return currAnn;
            }
        })
    }

    function pushAnnotationStateToUndoStack(annotation: Annotation) {
        setCurrentAnnotation((currAnn: CurrentAnnotation | null) => {
            if (currAnn === null) return null;
            else {
                return currAnn.addAnnotation(annotation);
            }
        });
    }

    function handleConfirmImport() {
        // Set activeModal to null
        setActiveModal(null);

        // POST new annotations as ground truth
        // if (!highlightedPreds) return;
        postAnnotations(currentImage.id, currentAnnotationClass?.id, highlightedPreds?.map(ann => ann.parsedPolygon)).then((resp) => {
            setHighlightedPreds(null);
        });

    }

    function handleCancelImport() {
        setActiveModal(null);
        setHighlightedPreds(null);
    }

    async function handleDeleteClass() {
        const deleteResp = await deleteAnnotationClass(currentAnnotationClass?.id)
        if (deleteResp.status !== 204) {
            console.error("Error deleting annotation class:", deleteResp);
            return;
        }
        const getResp = await searchAnnotationClasses(currentProject.id);
        if (getResp.status !== 200) {
            console.error("Error fetching annotation classes:", getResp);
            return;
        }
        setAnnotationClasses(getResp.data);
        const newCurrentAnnotationClass = getResp.data.find((c) => c.id === DEFAULT_CLASS_ID);
        if (!newCurrentAnnotationClass) {
            console.error("Error: Default annotation class not found");
            return;
        }
        setCurrentAnnotationClass(newCurrentAnnotationClass);  // Assumed to be the tissue mask class
        setActiveModal(null);
    }

    function handleCancelDeleteClass() {
        setActiveModal(null);
    }


    function handleCancelExport() {
        setActiveModal(null);
    }


    // useHotkeys('ctrl', () => setCtrlHeld(true), { keydown: true, keyup: false });
    // useHotkeys('ctrl', () => setCtrlHeld(false), { keydown: false, keyup: true });
    useHotkeys('1', () => setCurrentTool(TOOLBAR_KEYS.POINTER), { keydown: true });
    useHotkeys('2', () => setCurrentTool(TOOLBAR_KEYS.IMPORT), { keydown: true });
    useHotkeys('3', () => setCurrentTool(TOOLBAR_KEYS.BRUSH), { keydown: true });
    // useHotkeys('4', () => setCurrentTool(TOOLBAR_KEYS.WAND), { keydown: true });
    useHotkeys('5', () => setCurrentTool(TOOLBAR_KEYS.POLYGON), { keydown: true });

    useEffect(() => {
        if (projectid && imageid) {
            fetchProject(parseInt(projectid)).then((resp) => {
                setCurrentProject(resp.data);
            });
    
            fetchImage(parseInt(imageid)).then((resp) => {
                setCurrentImage(resp.data);
            });
        }

        searchAnnotationClasses(Number(projectid)).then((resp) => {
            setAnnotationClasses(resp.data);
            setCurrentAnnotationClass(resp.data.find((c) => c.id === DEFAULT_CLASS_ID) || null); // Set the current annotation class to the default one
        });
        
    }, [])

    useEffect(() => {
        const currentAnnotationClassId = currentAnnotationClass?.id;
        // Check if the current annotation class is valid
        if (!currentAnnotationClassId || currentAnnotationClassId === MASK_CLASS_ID) return;
        setCurrentTool(TOOLBAR_KEYS.POINTER);
        
        startProcessingAnnotationClass(currentAnnotationClass?.id).then((resp) => {
            if (resp.status === 200) {
                console.log("Processing started");
            }
        });
    }
    , [currentAnnotationClass]);


    if (currentImage) {
        return (
            <>
                <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                    <ConfirmationModal activeModal={activeModal} config={MODAL_DATA.IMPORT_CONF} onConfirm={handleConfirmImport} onCancel={handleCancelImport} checkboxCookieName={COOKIE_NAMES.SKIP_CONFIRM_IMPORT}/>
                    <NewClassModal activeModal={activeModal} setActiveModal={setActiveModal} config={MODAL_DATA.ADD_CLASS} currentProject={currentProject} annotationClasses={annotationClasses} setAnnotationClasses={setAnnotationClasses}/>
                    <ConfirmationModal activeModal={activeModal} config={MODAL_DATA.DELETE_CLASS} onConfirm={handleDeleteClass} onCancel={handleCancelDeleteClass} checkboxCookieName={COOKIE_NAMES.SKIP_CONFIRM_DELETE_CLASS}/>
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
                                }}>
                                    <Toolbar {...{ currentTool, 
                                                setCurrentTool,
                                                ctrlHeld }} />
                                </Card.Header>
                                <Card.Body style={{ padding: "0px" }}>
                                    <ViewportMap {...{ currentImage, 
                                                    currentAnnotationClass, 
                                                    gts, 
                                                    setGts, 
                                                    preds, 
                                                    setPreds, 
                                                    currentTool, 
                                                    setCurrentTool,
                                                    ctrlHeld,
                                                    setCtrlHeld,
                                                    currentAnnotation, 
                                                    setCurrentAndPreviousAnnotation, 
                                                    pushAnnotationStateToUndoStack,
                                                    prevCurrentAnnotation,
                                                    highlightedPreds,
                                                    setHighlightedPreds,
                                                    activeModal,
                                                    setActiveModal,
                                                    setMouseCoords
                                                    }} />
                                    <Legend mouseCoords={mouseCoords}/>
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