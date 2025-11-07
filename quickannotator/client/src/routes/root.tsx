import { Outlet } from 'react-router-dom';
import { useState } from 'react';
import Navigation from '../components/navigation.tsx';
import { Project, Image } from '../types.ts';
import { CookiesProvider } from 'react-cookie';
import { toast, ToastContainer } from 'react-toastify';

function addPendingToast() {
    const checkCondition = async () => {
        try {
            const response = await fetch('/api/check-condition'); // Replace with your endpoint
            const data = await response.json();
            if (data.conditionMet) {
                return Promise.resolve();
            } else {
                throw new Error('Condition not met');
            }
        } catch (error) {
            throw new Error('Error checking condition');
        }
    };

    const pollCondition = () =>
        new Promise(async (resolve, reject) => {
            const interval = setInterval(async () => {
                try {
                    await checkCondition();
                    clearInterval(interval);
                    resolve('Condition met');
                } catch (error) {
                    // Keep polling until condition is met
                }
            }, 3000); // Poll every 3 seconds
        });

    toast.promise(
        pollCondition(),
        {
            pending: 'Checking condition...',
            success: 'Condition met 👌',
            error: 'Failed to meet condition 🤯',
        }
    );
}

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
            <ToastContainer position='bottom-right' newestOnTop/>
            <Outlet context={{ currentProject, setCurrentProject, currentImage, setCurrentImage }} />
            <button 
                onClick={addPendingToast} 
                style={{ position: 'absolute', bottom: '20px', right: '20px' }}
            >
                Test Toast
            </button>
        </div>
    );
}
