import { useState } from 'react';
import { Button, Spinner } from 'react-bootstrap';
import { PauseFill, PlayFill } from 'react-bootstrap-icons';
import { DLActorStatus } from '../types';
import { setEnableTraining } from '../helpers/api';
import './TrainingStatusButton.css';

interface Props {
    currentDlActorStatus: DLActorStatus | null;
    setCurrentDlActorStatus: (status: DLActorStatus | null) => void;
    annotationClassId: number | undefined;
}

const TrainingStatusButton = ({ currentDlActorStatus, setCurrentDlActorStatus, annotationClassId }: Props) => {
    const [isLoading, setIsLoading] = useState(false);
    const [isHovered, setIsHovered] = useState(false);

    const handleToggleTraining = async () => {
        if (!annotationClassId || currentDlActorStatus === null) return;
        
        setIsLoading(true);
        try {
            const newEnableValue = !currentDlActorStatus.enable_training;
            const response = await setEnableTraining(annotationClassId, newEnableValue);
            if (response.status === 200) {
                setCurrentDlActorStatus(response.data);
            }
        } catch (error) {
            console.error('Error toggling training status:', error);
        } finally {
            setIsLoading(false);
        }
    };

    // Training unavailable state
    if (currentDlActorStatus === null) {
        return (
            <Button 
                variant="secondary" 
                size="sm" 
                disabled
                className="training-status-btn"
            >
                Training Unavailable
            </Button>
        );
    }

    const isTrainingActive = currentDlActorStatus.enable_training && currentDlActorStatus.proc_running_since !== null;

    return (
        <Button
            variant={isTrainingActive ? "success" : "warning"}
            size="sm"
            className={`training-status-btn ${isTrainingActive ? 'training-active' : ''}`}
            onClick={handleToggleTraining}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            disabled={isLoading}
        >
            {isLoading ? (
                <Spinner animation="border" size="sm" />
            ) : isHovered ? (
                isTrainingActive ? (
                    <><PauseFill className="me-1" /> Pause</>
                ) : (
                    <><PlayFill className="me-1" /> Resume</>
                )
            ) : (
                isTrainingActive ? 'Training Active' : 'Training Frozen'
            )}
        </Button>
    );
};

export default TrainingStatusButton;
