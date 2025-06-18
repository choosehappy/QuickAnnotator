import React, { useEffect, useState } from 'react';
import { Modal, Button, Form } from 'react-bootstrap';
import { AnnotationClass, ModalData, Project } from '../types';
import { createAnnotationClass, searchAnnotationClasses, fetchMagnifications, fetchNewColor, fetchTilesizes } from '../helpers/api';
import { useForm, SubmitHandler, FormProvider } from "react-hook-form";

interface IFormInput {
    formBasicName: string;
    formBasicColor: string;
    formBasicMagnification: string;
    formBasicTilesize: string;
}

interface NewClassModalProps {
    currentProject: Project;
    activeModal: number | null;
    config: ModalData;
    annotationClasses: AnnotationClass[];
    setAnnotationClasses: React.Dispatch<React.SetStateAction<AnnotationClass[]>>;
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
}

const NewClassModal: React.FC<NewClassModalProps> = (props: NewClassModalProps) => {
    const [magOptions, setMagOptions] = useState<number[]>([]);
    const [tilesizeOptions, setTilesizeOptions] = useState<number[]>([]);
    const [defaultColor, setDefaultColor] = useState<string>("#000000");
    const methods = useForm<IFormInput>(); // Initialize useForm with type

    useEffect(() => {
        if (!props.currentProject.id) return;
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

        // Fetch suggested tile size options from the server
        fetchTilesizes().then((resp) => {
            if (resp.status !== 200) {
                console.error("Error fetching tile size options:", resp);
                return;
            }
            setTilesizeOptions(resp.data.tilesizes);
        });
    }, [props.annotationClasses]);

    const onSubmit: SubmitHandler<IFormInput> = async (data) => {
        try {
            console.log("Form data:", data);
            const createResp = await createAnnotationClass(
                props.currentProject.id,
                data.formBasicName,
                data.formBasicColor,
                parseInt(data.formBasicMagnification),
                parseInt(data.formBasicTilesize)
            );

            if (createResp.status !== 201) {
                console.error("Error creating annotation class:", createResp);
                alert("Failed to create annotation class. Please try again.");
                return;
            }

            const fetchResp = await searchAnnotationClasses(props.currentProject.id);
            if (fetchResp.status !== 200) {
                console.error("Error fetching annotation classes:", fetchResp);
                alert("Failed to fetch updated annotation classes. Please refresh the page.");
                return;
            }

            props.setAnnotationClasses(fetchResp.data);
            methods.reset(); // Reset the form after successful submission
            props.setActiveModal(null);
        } catch (error) {
            console.error("Unexpected error:", error);
            alert("An unexpected error occurred. Please try again later.");
        }
    };

    function onCancel() {
        methods.reset(); // Reset the form when the modal is closed
        props.setActiveModal(null);
    }

    return (
        <Modal show={props.activeModal === props.config.id} onHide={onCancel} backdrop={false}>
            <Modal.Header closeButton>
                <Modal.Title>{props.config.title}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <p>{props.config.description}</p>
                <FormProvider {...methods}>
                    <Form onSubmit={methods.handleSubmit(onSubmit)}>
                        <Form.Group controlId="formBasicName">
                            <Form.Label>Name</Form.Label>
                            <Form.Control
                                type="text"
                                placeholder="Enter class name"
                                {...methods.register("formBasicName")}
                            />
                        </Form.Group>
                        <Form.Group controlId="formBasicColor">
                            <Form.Label>Color</Form.Label>
                            <Form.Control
                                type="color"
                                defaultValue={defaultColor}
                                {...methods.register("formBasicColor")}
                            />
                        </Form.Group>
                        <Form.Group controlId="formBasicMagnification">
                            <Form.Label>Magnification</Form.Label>
                            <Form.Control
                                as="select"
                                defaultValue=""
                                {...methods.register("formBasicMagnification")}
                            >
                                <option value="" disabled>Select magnification</option>
                                {magOptions.map((option, index) => (
                                    <option key={index} value={option}>
                                        {option}x
                                    </option>
                                ))}
                            </Form.Control>
                        </Form.Group>
                        <Form.Group controlId="formBasicTilesize">
                            <Form.Label>Tile Size</Form.Label>
                            <Form.Control
                                as="select"
                                defaultValue=""
                                {...methods.register("formBasicTilesize")}
                            >
                                <option value="" disabled>Select tile size</option>
                                {tilesizeOptions.map((option, index) => (
                                    <option key={index} value={option}>
                                        {option}
                                    </option>
                                ))}
                            </Form.Control>
                        </Form.Group>
                        <Modal.Footer>
                            <Button variant="secondary" onClick={onCancel}>
                                Cancel
                            </Button>
                            <Button variant="primary" type="submit">
                                Confirm
                            </Button>
                        </Modal.Footer>
                    </Form>
                </FormProvider>
            </Modal.Body>
        </Modal>
    );
};

export default NewClassModal;