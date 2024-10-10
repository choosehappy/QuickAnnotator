import Project from '../types/project.ts';
import Image from '../types/image.ts';
import {Link} from "react-router-dom";
// import BreadCrumb from 'react-bootstrap/Breadcrumb';
import Navbar from 'react-bootstrap/Navbar';
import Nav from 'react-bootstrap/Nav';
import NavItem from 'react-bootstrap/NavItem';
import { ReactNode } from "react";


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
                <i className="bi bi-caret-right-fill"></i>
            </NavItem>
            {children}
        </>
    )
}


const Navigation = (props: NavbarProps) => {
    return (
        <>
            <span>
                <Navbar expand='lg' className='bg-body-secondary'>
                    <Nav className='me-auto'>
                        <Navbar.Brand as={Link} to="/home">Quick Annotator</Navbar.Brand>
                        {props.currentProject && <Item><Nav.Link as={Link} to="/project">{props.currentProject?.name}</Nav.Link></Item>}
                        {props.currentImage && <Item><Nav.Link as={Link} to="/annotate" >{props.currentImage?.name}</Nav.Link></Item>}
                    </Nav>
                </Navbar>
            </span>
        </>
    )
}

export default Navigation