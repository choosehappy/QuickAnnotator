import React, { useState } from 'react';
import { Modal, Button, Form } from 'react-bootstrap';
import { ModalData } from '../types';

interface ConfirmationModalProps {
    activeModal: number | null;
    config: ModalData;
    onConfirm: () => void;
    onCancel: () => void;
    onDoNotShowAgainChange?: (checked: boolean) => void;
}

const ConfirmationModal: React.FC<ConfirmationModalProps> = (props: ConfirmationModalProps) => {
    const [doNotShowAgain, setDoNotShowAgain] = useState(false);

    const handleCheckboxChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setDoNotShowAgain(event.target.checked);
        if (props.onDoNotShowAgainChange) {
            props.onDoNotShowAgainChange(event.target.checked);
        }
    };

    return (
        <Modal show={props.activeModal === props.config.id} onHide={props.onCancel} backdrop={false}>
            <Modal.Header closeButton>
                <Modal.Title>{props.config.title}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <p>{props.config.description}</p>
                <Form.Check 
                    type="checkbox" 
                    label="Do not show again" 
                    checked={doNotShowAgain} 
                    onChange={handleCheckboxChange} 
                />
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={props.onCancel}>
                    Cancel
                </Button>
                <Button variant="primary" onClick={props.onConfirm}>
                    Confirm
                </Button>
            </Modal.Footer>
        </Modal>
    );
};

export default ConfirmationModal;