import React, { useState } from 'react';
import { Modal, Button, Form } from 'react-bootstrap';
import { AnnotationClass, ModalData, Project } from '../types';
import { createAnnotationClass, fetchAnnotationClasses } from '../helpers/api';

interface NewClassModalProps {
    currentProject: Project;
    activeModal: number | null;
    config: ModalData;
    setClasses: React.Dispatch<React.SetStateAction<AnnotationClass[]>>;
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
}

const NewClassModal: React.FC<NewClassModalProps> = (props: NewClassModalProps) => {

    function onSubmit() {
        createAnnotationClass(props.currentProject.id, "New Class", "#000000", 1).then((resp) => {});
        fetchAnnotationClasses().then((resp) => {
            props.setClasses(resp.data);
        });
        props.setActiveModal(null);
        
    }

    function onCancel() {
        props.setActiveModal(null);
    }

    return (
        <Modal show={props.activeModal === props.config.id} onHide={onCancel} backdrop={false}>
            <Modal.Header closeButton>
                <Modal.Title>{props.config.title}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onCancel}>
                    Cancel
                </Button>
                <Button variant="primary" type='submit'>
                    Confirm
                </Button>
            </Modal.Footer>
        </Modal>
    );
};

export default NewClassModal;