import { Modal, Form, Button } from "react-bootstrap";

interface ExportAnnotationsModal {
    show: boolean;
    handleClose: () => void;
}

const ExportAnnotationsModal = (props: ExportAnnotationsModal) => {
    return (
        <Modal show={props.show} onHide={props.handleClose} size="sm" centered>
            <Modal.Header closeButton>
                <Modal.Title>Export Annotations

                </Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form>
                    <Form.Group>
                        <Form.Label>Annotations Export Format</Form.Label>
                        <Form.Select>
                            <option value="1">GeoJSON</option>
                            <option value="2">CSV</option>
                            <option value="3">XML</option>
                        </Form.Select>
                    </Form.Group>

                    <Form.Group>
                        <Form.Label>Metrics Export Format</Form.Label>
                        <Form.Select>
                            <option value="1">Do not export metrics</option>
                            <option value="2">export metrics</option>
                        </Form.Select>
                    </Form.Group>

                    <Form.Group>
                        <Form.Label>Metrics Export Format</Form.Label>
                        <Form.Check type="radio" label="Save Locally"/>
                        <Form.Check type="radio" label="Save Remotely" disabled/>
                        <Form.Control className="form-control form-control-sm" placeholder="Input Remote Path" disabled/>
                    </Form.Group>
                </Form>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={props.handleClose}>
                    Close
                </Button>
                <Button variant="primary">
                    Export
                </Button>
            </Modal.Footer>
        </Modal>
    )
}

export default ExportAnnotationsModal

