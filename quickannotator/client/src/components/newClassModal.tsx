import React, { useEffect, useState } from 'react';
import { Modal, Button, Form } from 'react-bootstrap';
import { AnnotationClass, ModalData, Project } from '../types';
import { createAnnotationClass, fetchAnnotationClasses } from '../helpers/api';
import { useForm, FormProvider, useFormContext } from "react-hook-form";

interface NewClassModalProps {
    currentProject: Project;
    activeModal: number | null;
    config: ModalData;
    setAnnotationClasses: React.Dispatch<React.SetStateAction<AnnotationClass[]>>;
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
}

const NewClassModal: React.FC<NewClassModalProps> = (props: NewClassModalProps) => {
    // TODO: use react-query for managing API responses.
    useEffect(() => {
        fetchAnnotationClasses().then((resp) => {
            props.setAnnotationClasses(resp.data);
        });
    }, []);

    function onSubmit() {
        createAnnotationClass(props.currentProject.id, "New Class", "#000000", 1).then((resp) => {});
        fetchAnnotationClasses().then((resp) => {
            props.setAnnotationClasses(resp.data);
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
                <p>{props.config.description}</p>
                <FormProvider {...useForm()}>
                    <Form onSubmit={onSubmit}>
                        <Form.Group controlId="formBasicName">
                            <Form.Label>Name</Form.Label>
                            <Form.Control type="text" placeholder="Enter class name" />
                        </Form.Group>
                        <Form.Group controlId="formBasicColor">
                            <Form.Label>Color</Form.Label>
                            <Form.Control type="color" defaultValue="#000000" />
                        </Form.Group>
                        <Form.Group controlId="formBasicMagnification">
                            <Form.Label>Magnification</Form.Label>
                            <Form.Control as="select" defaultValue="">
                                <option value="" disabled>Select magnification</option>
                                <option value="10x">10x</option>
                                <option value="20x">20x</option>
                                <option value="40x">40x</option>
                                <option value="100x">100x</option>
                            </Form.Control>
                        </Form.Group>
                    </Form>
                </FormProvider>
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