import { Image, Project } from "../types.ts"
import {Link} from "react-router-dom";
// import BreadCrumb from 'react-bootstrap/Breadcrumb';
import Navbar from 'react-bootstrap/Navbar';
import Nav from 'react-bootstrap/Nav';
import NavItem from 'react-bootstrap/NavItem';
import Container from "react-bootstrap/Container";
import ProgressBar from "react-bootstrap/ProgressBar"

interface NavbarProps {
    currentProject: Project | null;
    setCurrentProject: (project: Project | null) => void;
    currentImage: Image | null;
    setCurrentImage: (image: Image | null) => void;
}

// @ts-ignore
const Item = ({ children }) => {
    return (
        <>
            <NavItem style={{alignItems: "center", display: "flex"}}>
                <i className="bi bi-caret-right-fill text-white"></i>
            </NavItem>
            {children}
        </>
    )
}


const Navigation = (props: NavbarProps) => {
    return (
        <>
            <Navbar bg="dark" data-bs-theme="dark">
                <Container fluid>
                    <Nav>
                        <Navbar.Brand as={Link} to="/">Quick Annotator</Navbar.Brand>
                        {props.currentProject && <Item><Nav.Link as={Link} to={`/project/${props.currentProject.id}`}>{props.currentProject.name}</Nav.Link></Item>}
                        {props.currentProject && props.currentImage && <Item><Nav.Link as={Link} to={`/project/${props.currentProject.id}/annotate/${props.currentImage.id}`} >{props.currentImage.name}</Nav.Link></Item>}
                    </Nav>
                    <Nav>
                        {props.currentImage && <Nav.Link>Previous Image</Nav.Link>}
                        {props.currentImage && <Nav.Link>Next Image</Nav.Link>}
                        {props.currentImage && <Nav.Item className="d-flex align-items-center"><ProgressBar now={60} label={`${60}%`} style={{ width: '150px', height: '10px' }} /></Nav.Item>}
                    </Nav>
                    <Nav className="justify-content-end">
                        <Nav.Link>Metrics</Nav.Link>
                        <Nav.Link>Notifications</Nav.Link>
                        <Nav.Link>Settings</Nav.Link>
                    </Nav>
                </Container>
            </Navbar>
        </>
    )
}

export default Navigation