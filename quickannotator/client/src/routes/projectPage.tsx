import Nav from 'react-bootstrap/Nav';
import { Link, useOutletContext, useParams } from "react-router-dom";
import { useEffect } from 'react';
import Container from "react-bootstrap/Container";
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";
import Card from "react-bootstrap/Card";
import Button from "react-bootstrap/Button";
import ListGroup from "react-bootstrap/ListGroup";

import { fetchProject } from "../helpers/api.ts"
import { OutletContextType } from "../types.ts";

const ProjectPage = () => {
    const { currentProject, setCurrentProject, currentImage, setCurrentImage } = useOutletContext<OutletContextType>();
    const imageid = 1;
    const { projectid } = useParams();

    useEffect(() => {
        setCurrentImage(null);
        fetchProject(parseInt(projectid)).then((resp) => {
            setCurrentProject(resp);
        })
    }, [])

    if (currentProject) {
        return (
            <>
                <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                    <Row className="d-flex flex-grow-1">
                        <Col className="d-flex flex-grow-1"><Card className="flex-grow-1">
                            <Card.Body>
                                <ListGroup>
                                    <Button><Nav.Link as={Link} to={`/project/${currentProject.id}/annotate/1`}>Image 1</Nav.Link></Button>
                                    <Button><Nav.Link as={Link} to={`/project/${currentProject.id}/annotate/2`}>Image 2</Nav.Link></Button>
                                </ListGroup>
                            </Card.Body>
                        </Card></Col>
                    </Row>
                </Container>
            </>
        )
    }
}

export default ProjectPage