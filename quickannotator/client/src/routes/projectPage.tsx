import Nav from 'react-bootstrap/Nav';
import { Link, useOutletContext, useParams } from "react-router-dom";
import { useEffect } from 'react';
import {Container, Row, Col, Card, ButtonToolbar, ButtonGroup, Button, ListGroup} from "react-bootstrap";
import { Fullscreen, ArrowCounterclockwise, GearFill, Download, AspectRatioFill, Brush, Magic, Eraser, Heptagon } from 'react-bootstrap-icons';

import { fetchProject } from "../helpers/api.ts"
import { OutletContextType } from "../types.ts";
import './project.css'

const ProjectPage = () => {
    // const { projectid } = useParams();
    // const { currentImage, setCurrentImage, setCurrentProject } = useOutletContext<OutletContextType>();

    // const [currentClass, setCurrentClass] = useState<AnnotationClass | null>(null);
    // const [gts, setGts] = useState<Annotation[]>([]);
    // const [preds, setPreds] = useState<Annotation[]>([]);
    // const [currentTool, setCurrentTool] = useState<string | null>('0');
    // const [action, setAction] = useState<string | null>(null);
    // const currentAnnotation = useRef<CurrentAnnotation | null>(null);

    // useEffect(() => {
    //     fetchProject(parseInt(projectid)).then((resp) => {
    //         setCurrentProject(resp);
    //     });

    //     fetchImage(parseInt(imageid)).then((resp) => {
    //         setCurrentImage(resp);
    //     });
    // }, [])

    // const { currentProject, setCurrentProject, currentImage, setCurrentImage } = useOutletContext<OutletContextType>();
    // const imageid = 1;
    // const { projectid } = useParams();

    // useEffect(() => {
    //     setCurrentImage(null);
    //     fetchProject(parseInt(projectid)).then((resp) => {
    //         setCurrentProject(resp);
    //     })
    // }, [])

    // if (currentProject) {
        return (
            <>
                <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                    <Row className="d-flex flex-grow-1">
                        <Col className="d-flex flex-grow-1">
                            <Card className="flex-grow-1">
                                <Card.Header >
                                <ButtonToolbar className="float-end" aria-label="Toolbar with button groups">
            <ButtonGroup className={"me-2"}>
                    <Button variant="secondary" title="Show Enbedding"><AspectRatioFill/></Button>
                    <Button variant="secondary" title="Export Annotations"><Download/></Button>
                    <Button variant="primary" title="Setting"><GearFill/></Button>
            </ButtonGroup>
            </ButtonToolbar>
                                </Card.Header>
                                <Card.Body>
                                    Table
                                </Card.Body>
                                <Card.Footer>
                                    footer<br/>
                                    footer<br/>
                                    footer
                                </Card.Footer>
                            </Card>
                        </Col>
                    </Row>
                </Container>
            </>
        )
    
}

export default ProjectPage