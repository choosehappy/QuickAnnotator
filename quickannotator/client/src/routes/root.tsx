import { Outlet } from 'react-router-dom';
import { useState } from 'react';
import Navigation from '../components/navigation.tsx';
import { Project, Image } from '../types.ts';
import { CookiesProvider } from 'react-cookie';

export default function Root() {
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
