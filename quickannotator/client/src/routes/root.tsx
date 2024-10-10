import { Link, Outlet } from 'react-router-dom';
import { useState } from 'react';
import Project from '../interfaces';

export default function Root() {


    const [currentProject, setCurrentProject] = useState<Project>();
    return (
        <>
            <div>This will be the navbar</div>
            <div>Current Project: {currentProject?.name}</div>
            <ul>
                <li><Link to={'/'}>Home</Link></li>
                <li><Link to={'/annotate'}>Annotation Page</Link></li>
                <li></li>

            </ul>
            <Outlet context={{currentProject, setCurrentProject}}/>
        </>
    )
}