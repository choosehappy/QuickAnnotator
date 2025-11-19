import { Image, Project } from "../types.ts"
import { useState } from 'react';
import NotificationCenter from './notificationCenter';
import {Link} from "react-router-dom";
// import BreadCrumb from 'react-bootstrap/Breadcrumb';
import Navbar from 'react-bootstrap/Navbar';
import Nav from 'react-bootstrap/Nav';
import NavItem from 'react-bootstrap/NavItem';
import Container from "react-bootstrap/Container";
import ProgressBar from "react-bootstrap/ProgressBar"
import { CaretRightFill } from 'react-bootstrap-icons';
import Badge from 'react-bootstrap/Badge';
import { BellFill } from 'react-bootstrap-icons';
import { useNotificationCenter } from 'react-toastify/addons/use-notification-center';

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
                <CaretRightFill className="text-white" />
            </NavItem>
            {children}
        </>
    )
}


const Navigation = (props: NavbarProps) => {
    const [showNotifications, setShowNotifications] = useState(false);
    // use the notification center hook here so we can render unread count in the navbar
    const notificationCenter = useNotificationCenter();
    const unread = (notificationCenter && notificationCenter.unreadCount) ? notificationCenter.unreadCount : 0;
    return (
        <>
            <Navbar bg="dark" data-bs-theme="dark">
                <Container fluid>
                    <Nav>
                        <Navbar.Brand as={Link} to="/">QuickAnnotator</Navbar.Brand>
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
                        <Nav.Link onClick={() => setShowNotifications(true)} className="position-relative d-flex align-items-center">
                            <BellFill className="text-white" />
                            {unread > 0 && (
                                <Badge bg="danger" pill style={{ position: 'absolute', top: '6px', right: '6px', transform: 'translate(50%,-50%)' }}>{unread}</Badge>
                            )}
                            <span className="ms-2">Notifications</span>
                        </Nav.Link>
                        <Nav.Link>Settings</Nav.Link>
                    </Nav>
                </Container>
            </Navbar>
            <NotificationCenter show={showNotifications} onHide={() => setShowNotifications(false)} notificationCenter={notificationCenter} />
        </>
    )
}

export default Navigation