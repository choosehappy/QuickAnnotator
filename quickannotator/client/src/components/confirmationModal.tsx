import React, { useState } from 'react';
import { Modal, Button, Form } from 'react-bootstrap';

interface ConfirmationModalProps {
    show: boolean;
    title: string;
    description: string;
    onConfirm: () => void;
    onCancel: () => void;
    onDoNotShowAgainChange?: (checked: boolean) => void;
}

const ConfirmationModal: React.FC<ConfirmationModalProps> = ({ show, title, description, onConfirm, onCancel, onDoNotShowAgainChange }) => {
    const [doNotShowAgain, setDoNotShowAgain] = useState(false);

    const handleCheckboxChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setDoNotShowAgain(event.target.checked);
        if (onDoNotShowAgainChange) {
            onDoNotShowAgainChange(event.target.checked);
        }
    };

    return (
        <Modal show={show} onHide={onCancel}>
            <Modal.Header closeButton>
                <Modal.Title>{title}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <p>{description}</p>
                <Form.Check 
                    type="checkbox" 
                    label="Do not show again" 
                    checked={doNotShowAgain} 
                    onChange={handleCheckboxChange} 
                />
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onCancel}>
                    Cancel
                </Button>
                <Button variant="primary" onClick={onConfirm}>
                    Confirm
                </Button>
            </Modal.Footer>
        </Modal>
    );
};

export default ConfirmationModal;