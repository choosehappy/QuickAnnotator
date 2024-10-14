import {Link, useOutletContext} from 'react-router-dom';
import {useEffect} from "react";
import {OutletContextType} from "../types/outlet.ts";
import {initialProject} from "../types/project.ts";
import Nav from "react-bootstrap/Nav";
import Container from "react-bootstrap/Container";
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";
import Card from "react-bootstrap/Card";

const LandingPage = () => {
    const {setCurrentImage, setCurrentProject} = useOutletContext<OutletContextType>();
    useEffect(() => {
        setCurrentImage(null);
        setCurrentProject(null);
    });

    return (
        <>
            <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                <Row className="d-flex flex-grow-1">
                    <Col className="d-flex flex-grow-1"><Card className="flex-grow-1">
                        <Card.Body>
                            <Nav.Link as={Link} to={'/project'} onClick={() => setCurrentProject(initialProject)}>Enter Project</Nav.Link>
                        </Card.Body>
                    </Card></Col>
                </Row>
            </Container>
        </>
    )
}


export default LandingPage