import { Outlet, useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Navigation from '../components/navigation.tsx';
import Project, { initialProject } from '../types/project.ts';
import Image, { initialImage } from '../types/image.ts';

export default function Root() {
    const { projectid, imageid } = useParams(); // Extract URL params
    const [currentProject, setCurrentProject] = useState<Project | null>(null);
    const [currentImage, setCurrentImage] = useState<Image | null>(null);

    return (
        <div className="d-flex flex-column" style={{ height: '100vh' }}>
            <Navigation
                {...{
                    currentProject,
                    setCurrentProject,
                    currentImage,
                    setCurrentImage,
                }}
            />
            <Outlet context={{ currentProject, setCurrentProject, currentImage, setCurrentImage }} />
        </div>
    );
}
