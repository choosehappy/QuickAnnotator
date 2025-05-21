import { Modal, Form, Button } from "react-bootstrap";
import { PROJECT_EDIT_MODAL_DATA, PROJECT_CONFIG_OPTIONS } from "../../../../helpers/config";
import { useState, useEffect } from "react";
import { Project } from "../../../../types";

interface ConfigModal {
    show: boolean;
    data: undefined | Project;
    status: undefined | number; // 0 - create, 1 - edit
    closeHandle: () => void;
    submitHandle: (e: React.MouseEvent<HTMLButtonElement>) => Promise<void>;
}

interface ProjectDataForm {
    name: string;
    is_dataset_large: false;
    description: string;
}

const ConfigModal = (props: ConfigModal) => {
    const [formData, setFormData] = useState<ProjectDataForm>({
        name: '',
        is_dataset_large: false,
        description: ''
    });
    const { show, status, data = {}, closeHandle, submitHandle } = props

    useEffect(() => {
        // Populate form with incoming data when modal is shown
        if (show) {
            setFormData({
                name: data?.name || '',
                is_dataset_large: data?.is_dataset_large || false,
                description: data?.description || '',
            });
        }
    }, [data]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: value,
        }));
    };
    return (
        <Modal show={show} onHide={closeHandle}>
            <Form onSubmit={submitHandle}>
                <Modal.Header closeButton>
                    <Modal.Title>{status ? PROJECT_EDIT_MODAL_DATA.EDIT.title : PROJECT_EDIT_MODAL_DATA.ADD.title}
                    </Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <Form.Text className="text-muted">
                        {status ? PROJECT_EDIT_MODAL_DATA.EDIT.text : PROJECT_EDIT_MODAL_DATA.ADD.text}
                    </Form.Text>
                    <Form.Group className="mb-3">
                        <Form.Label>Name</Form.Label>
                        <Form.Control name="name" type="text" value={formData.name}
                            onChange={handleChange} placeholder="Enter Project Name" />
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Label>Dataset Size</Form.Label>
                        <Form.Select name="is_dataset_large" value={formData.is_dataset_large} onChange={handleChange}>
                            {/* <option value="false" >{"< 1000 Whole Slide Images"}</option>
                            <option value="true" >{"> 1000 Whole Slide Images"}</option> */}
                            {PROJECT_CONFIG_OPTIONS.map(opt => <option value={opt.value}>{opt.text}</option>)}
                        </Form.Select>
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Label>Description</Form.Label>
                        <Form.Control name="description" as="textarea" value={formData.description} onChange={handleChange} placeholder="Enter Project Description" rows={3} />
                    </Form.Group>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={closeHandle}>
                        Cancel
                    </Button>
                    <Button variant="primary" type="submit">
                        {status ? PROJECT_EDIT_MODAL_DATA.EDIT.btnText : PROJECT_EDIT_MODAL_DATA.ADD.btnText}
                    </Button>
                </Modal.Footer>
            </Form>
        </Modal>
    )
}

export default ConfigModal

