import Container from 'react-bootstrap/Container'
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Stack from 'react-bootstrap/Stack';
import ClassesPane from "../components/classesPane.tsx";
import GroundTruthPane from "../components/groundTruthPane.tsx";
import PredictionsPane from "../components/predictionsPane.tsx";
import ViewportPane from "../components/viewportPane.tsx";

const AnnotationPage = () => {
    return (
        <>
            <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                <Row className="d-flex flex-grow-1">
                    <Col className="d-flex flex-grow-1"><ViewportPane/></Col>
                    <Col xs={3}>
                        <Stack gap={3}>
                            <ClassesPane/>
                            <GroundTruthPane/>
                            <PredictionsPane/>
                        </Stack>
                    </Col>
                </Row>
            </Container>
        </>
    )
}

export default AnnotationPage