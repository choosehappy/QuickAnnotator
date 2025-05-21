import { Modal, Button } from "react-bootstrap";
import { PROJECT_EDIT_MODAL_DATA } from "../../../../helpers/config";

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
            {PROJECT_EDIT_MODAL_DATA.REMOVE.title}
            </Modal.Header>
            <Modal.Body>{PROJECT_EDIT_MODAL_DATA.REMOVE.text}</Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={closeHandle}>
                    Cancel
                </Button>
                <Button variant="danger" onClick={submitHandle}>
                    {PROJECT_EDIT_MODAL_DATA.REMOVE.btnText}
                </Button>
            </Modal.Footer>
        </Modal>
    )
}

export default DeleteModal

