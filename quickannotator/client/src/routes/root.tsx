import { Outlet } from 'react-router-dom';
import { useState } from 'react';
import Navigation from '../components/navigation.tsx';
import Project, {initialProject} from '../types/project.ts';
import Image, {initialImage} from '../types/image.ts';

export default function Root() {


    const [currentProject, setCurrentProject] = useState<Project | null>(initialProject);
    const [currentImage, setCurrentImage] = useState<Image | null>(initialImage);
    return (
        <div className="d-flex flex-column" style={{height: '100vh'}}>
            <Navigation {...{currentProject, setCurrentProject, currentImage, setCurrentImage}}/>
            <Outlet context={{currentProject, setCurrentProject, currentImage, setCurrentImage}}/>
        </div>
    )
}