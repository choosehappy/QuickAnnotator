import React, { useEffect, useState } from 'react';
import { Modal, Button, Form } from 'react-bootstrap';
import { AnnotationClass, ModalData, Project } from '../types';
import { createAnnotationClass, fetchAnnotationClasses, fetchMagnifications, fetchNewColor } from '../helpers/api';
import { useForm, FormProvider, useFormContext } from "react-hook-form";

interface NewClassModalProps {
    currentProject: Project;
    activeModal: number | null;
    config: ModalData;
    setAnnotationClasses: React.Dispatch<React.SetStateAction<AnnotationClass[]>>;
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
}

const NewClassModal: React.FC<NewClassModalProps> = (props: NewClassModalProps) => {
    const [magOptions, setMagOptions] = useState<number[]>([]);
    const [defaultColor, setDefaultColor] = useState<string>("#000000");
    // TODO: use react-query for managing API responses.
    useEffect(() => {
        // Fetch suggested magnification options from the server
        fetchMagnifications().then((resp) => {
            if (resp.status !== 200) {
                console.error("Error fetching magnification options:", resp);
                return;
            }
            setMagOptions(resp.data.magnifications);
        });

        fetchNewColor(props.currentProject.id).then((resp) => {
            if (resp.status !== 200) {
                console.error("Error fetching new color:", resp);
                return;
            }
            setDefaultColor(resp.data.color);
        });

        // Fetch suggested color from the server

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
                            <Form.Control type="color" defaultValue={defaultColor} />
                        </Form.Group>
                        <Form.Group controlId="formBasicMagnification">
                            <Form.Label>Magnification</Form.Label>
                            <Form.Control as="select" defaultValue="">
                                <option value="" disabled>Select magnification</option>
                                {magOptions.map((option, index) => (
                                    <option key={index} value={option}>
                                        {option}x
                                    </option>
                                ))}
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