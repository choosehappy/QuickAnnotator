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

import { fetchImage, fetchProject } from "../helpers/api.ts";
import { Annotation, AnnotationClass, OutletContextType, CurrentAnnotation } from "../types.ts";
import { MODAL_DATA } from '../helpers/config.ts';
import Card from "react-bootstrap/Card";
import Toolbar from "../components/toolbar.tsx";

function usePrevious<T>(value: T): T | undefined {
    const ref = useRef<T>();
    useEffect(() => {
        ref.current = value;
    }, [value]);
    return ref.current;
}

const 

const AnnotationPage = () => {
    const { projectid, imageid } = useParams();
    const { currentImage, setCurrentImage, setCurrentProject } = useOutletContext<OutletContextType>();

    const [currentClass, setCurrentClass] = useState<AnnotationClass | null>(null);
    const [gts, setGts] = useState<Annotation[]>([]);
    const [preds, setPreds] = useState<Annotation[]>([]);
    const [currentTool, setCurrentTool] = useState<string | null>('0');
    const [action, setAction] = useState<string | null>(null);
    const [currentAnnotation, setCurrentAnnotation] = useState<CurrentAnnotation | null>(null);
    const [highlightedPreds, setHighlightedPreds] = useState<Annotation[]>([]);
    const prevCurrentAnnotation = usePrevious<CurrentAnnotation | null>(currentAnnotation);
    const [activeModal, setActiveModal] = useState<ANN_PAGE_MODALS | null>(null);

    useEffect(() => {
        if (projectid && imageid) {
            fetchProject(parseInt(projectid)).then((resp) => {
                setCurrentProject(resp.data);
            });
    
            fetchImage(parseInt(imageid)).then((resp) => {
                setCurrentImage(resp.data);
            });
        }
    }, [])

    if (currentImage) {
        return (
            <>
                <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                    <ConfirmationModal show={activeModal === MODAL_DATA.IMPORT_CONF.id} title={MODAL_DATA.IMPORT_CONF.title} description={MODAL_DATA.IMPORT_CONF.description}/>
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
                                                    currentClass, 
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
                                    {...{ currentClass, setCurrentClass }}
                                />
                                <GroundTruthPane
                                    {...{ gts, setGts, currentAnnotation, setCurrentAnnotation }}
                                />
                                <PredictionsPane
                                    {...{ preds, setPreds, currentAnnotation }}
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