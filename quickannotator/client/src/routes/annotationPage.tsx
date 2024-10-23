import Container from 'react-bootstrap/Container'
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Stack from 'react-bootstrap/Stack';
import ClassesPane from "../components/classesPane.tsx";
import GroundTruthPane from "../components/groundTruthPane.tsx";
import PredictionsPane from "../components/predictionsPane.tsx";
import ViewportPane from "../components/viewportPane.tsx";
import { useState, useEffect } from 'react';
import { useOutletContext, useParams } from 'react-router-dom';

import { fetchImage, fetchProject, fetchAllAnnotations } from "../helpers/api.ts";
import { Annotation, AnnotationClass, OutletContextType} from "../types.ts";


const AnnotationPage = () => {
    const { projectid, imageid } = useParams();
    const { currentImage, setCurrentImage, setCurrentProject } = useOutletContext<OutletContextType>();

    const [currentClass, setCurrentClass] = useState<AnnotationClass | null>(null);
    const [gts, setGts] = useState<Annotation[]>([]);
    const [preds, setPreds] = useState<Annotation[]>([]);

    useEffect(() => {
        fetchProject(parseInt(projectid)).then((resp) => {
            setCurrentProject(resp);
        });

        fetchImage(parseInt(imageid)).then((resp) => {
            setCurrentImage(resp);
        });
    }, [])

    useEffect(() => {
        if (currentImage && currentClass) {
            fetchAllAnnotations(currentImage.id, currentClass.id, true).then((resp) => {
                setGts(resp);
            })

            fetchAllAnnotations(currentImage.id, currentClass.id, false).then((resp) => {
                setPreds(resp);
            })
        }
    }, [currentImage, currentClass])

    if (currentImage) {
        return (
            <>
                <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                    <Row className="d-flex flex-grow-1">
                        <Col className="d-flex flex-grow-1">
                            <ViewportPane
                                {...{currentImage, currentClass, gts, preds}}
                            /></Col>
                        <Col xs={3}>
                            <Stack gap={3}>
                                <ClassesPane
                                    {...{currentClass, setCurrentClass}}
                                />
                                <GroundTruthPane
                                    {...{gts, setGts}}
                                />
                                <PredictionsPane
                                    {...{preds, setPreds}}
                                />
                            </Stack>
                        </Col>
                    </Row>
                </Container>
            </>
        )
    }
}

export default AnnotationPage