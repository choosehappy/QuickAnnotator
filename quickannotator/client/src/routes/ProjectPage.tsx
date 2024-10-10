import { useOutletContext } from 'react-router-dom';
import Project from '../types/project.ts';
import Image, {initialImage} from '../types/image.ts';
import Nav from 'react-bootstrap/Nav';
import {Link} from "react-router-dom";
import { useEffect } from 'react';
import { OutletContextType } from '../types/outlet.ts';

const ProjectPage = () => {
    const {setCurrentImage} = useOutletContext<OutletContextType>();
    useEffect(() => {
       setCurrentImage(null);
    });

    return (
        <>
            <div>This will be the project page</div>
            <Nav.Link as={Link} to={'/annotate'} onClick={() => setCurrentImage(initialImage)}>Begin annotation</Nav.Link>
        </>
    )
}

export default ProjectPage