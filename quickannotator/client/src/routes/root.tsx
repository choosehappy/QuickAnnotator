import { Outlet } from 'react-router-dom';
import { useState } from 'react';
import Navigation from '../components/navigation.tsx';
import { Project, Image } from '../types.ts';
import { CookiesProvider } from 'react-cookie';
import { ToastContainer } from 'react-toastify';
import { useNotificationCenter } from "react-toastify/addons/use-notification-center";

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
            <ToastContainer
                position="bottom-right"
                autoClose={5000}
                hideProgressBar={false}
                newestOnTop={false}
                closeOnClick={false}
                rtl={false}
                pauseOnFocusLoss
                draggable
                pauseOnHover
                theme="light"
            />
            <Outlet context={{ currentProject, setCurrentProject, currentImage, setCurrentImage }} />
        </div>
    );
}
