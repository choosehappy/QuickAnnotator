import { Modal, Button } from "react-bootstrap";

interface DeleteModal {
    show: boolean;
    closeHandle: () => void;
    submitHandle: (e: React.MouseEvent<HTMLButtonElement>) => Promise<void>;
}

const DeleteModal = (props: DeleteModal) => {
    const { show, closeHandle, submitHandle } = props
    return (
        <Modal show={show} onHide={closeHandle}>
            <Modal.Header closeButton>
                {/* <Modal.Title>Are You</Modal.Title> */}
            </Modal.Header>
            <Modal.Body>Are you sure you want to delete this project?</Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={closeHandle}>
                    Cancel
                </Button>
                <Button variant="danger" onClick={submitHandle}>
                    Delete
                </Button>
            </Modal.Footer>
        </Modal>
    )
}

export default DeleteModal

