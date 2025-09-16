import React, { useState } from 'react';
import { Modal, Button, Form } from 'react-bootstrap';
import { ModalData } from '../types';
import { useCookies } from 'react-cookie';
import { COOKIE_NAMES } from '../helpers/config';


interface ConfirmationModalProps {
    activeModal: number | null;
    config: ModalData;
    onConfirm: () => void;
    onCancel: () => void;
    checkboxCookieName: COOKIE_NAMES;
}

const ConfirmationModal: React.FC<ConfirmationModalProps> = (props: ConfirmationModalProps) => {
    const [cookies, setCookies] = useCookies([props.checkboxCookieName]);

    const handleCheckboxChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const isChecked = event.target.checked;
        setCookies(props.checkboxCookieName, isChecked, {path: '/' });
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