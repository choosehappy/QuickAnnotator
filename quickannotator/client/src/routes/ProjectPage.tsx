import { useOutletContext } from 'react-router-dom';
import {initialImage} from '../types/image.ts';
import Nav from 'react-bootstrap/Nav';
import {Link} from "react-router-dom";
import { useEffect } from 'react';
import { OutletContextType } from '../types/outlet.ts';
import Container from "react-bootstrap/Container";
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";
import Card from "react-bootstrap/Card";

const ProjectPage = () => {
    const {setCurrentImage} = useOutletContext<OutletContextType>();
    useEffect(() => {
       setCurrentImage(null);
    });

    return (
        <>
            <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                <Row className="d-flex flex-grow-1">
                    <Col className="d-flex flex-grow-1"><Card className="flex-grow-1">
                        <Card.Body>
                            <Nav.Link as={Link} to={'/annotate'} onClick={() => setCurrentImage(initialImage)}>Begin annotation</Nav.Link>
                        </Card.Body>
                    </Card></Col>
                </Row>
            </Container>
        </>
    )
}

export default ProjectPage