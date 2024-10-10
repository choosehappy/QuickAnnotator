import {Link, useOutletContext} from 'react-router-dom';
import {useEffect} from "react";
import {OutletContextType} from "../types/outlet.ts";
import {initialProject} from "../types/project.ts";
import Nav from "react-bootstrap/Nav";

const LandingPage = () => {
    const {setCurrentImage, setCurrentProject} = useOutletContext<OutletContextType>();
    useEffect(() => {
        setCurrentImage(null);
        setCurrentProject(null);
    });

    return (
        <>
            <div>This will be the landing page</div>
            <Nav.Link as={Link} to={'/project'} onClick={() => setCurrentProject(initialProject)}>Enter Project</Nav.Link>
        </>
    )
}

export default LandingPage