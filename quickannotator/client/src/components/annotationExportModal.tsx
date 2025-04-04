import React, { useState } from "react";
import { Modal, Button, Form } from 'react-bootstrap';
import { MODAL_DATA } from "../helpers/config";

enum ExportOption {
    LOCAL = "local",
    REMOTE = "remote",
    DSA = "dsa"
}

const exportOptions = {
    [ExportOption.LOCAL]: "Save locally",
    [ExportOption.REMOTE]: "Save remotely",
    [ExportOption.DSA]: "Push to Digital Slide Archive"
};

interface Props {
    show: boolean;
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
}

const AnnotationExportModal = (props: Props) => {
    const [selectedOption, setSelectedOption] = useState<ExportOption>(ExportOption.LOCAL);

    // TODO: consider splitting up the state according to selectedOption
    const [annotationsFormat, setAnnotationsFormat] = useState<string>("GeoJSON");
    const [metricsFormat, setMetricsFormat] = useState<string>("Do not export metrics");
    const [savePath, setSavePath] = useState<string>("");
    const [apiKey, setApiKey] = useState<string>("");
    const [collectionName, setCollectionName] = useState<string>("");
    const [folderName, setFolderName] = useState<string>("");

    const handleConfirm = () => {
        const data = {
            selectedOption,
            annotationsFormat,
            metricsFormat,
            savePath,
            apiKey,
            collectionName,
            folderName
        };

        if (selectedOption === ExportOption.LOCAL) {
            console.log("Exporting locally with data:", data);
        }
        else if (selectedOption === ExportOption.REMOTE) {
            console.log("Exporting remotely with data:", data);
        }
        else if (selectedOption === ExportOption.DSA) {
            console.log("Exporting to DSA with data:", data);
        }
    };

    const onCancel = () => {
        props.setActiveModal(null);
        setSelectedOption(ExportOption.LOCAL);
        setAnnotationsFormat("GeoJSON");
        setMetricsFormat("Do not export metrics");
        setSavePath("");
        setApiKey("");
        setCollectionName("");
        setFolderName("");
    };

    return (
        <Modal show={props.show} onHide={onCancel}>
            <Modal.Header closeButton>
                <Modal.Title>{MODAL_DATA.EXPORT_CONF.title}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <p>{MODAL_DATA.EXPORT_CONF.description}</p>
                <Form>
                    {Object.entries(exportOptions).map(([key, value]) => (
                        <Form.Check
                            key={key}
                            type="radio"
                            label={value}
                            name="exportOptions"
                            id={key}
                            checked={selectedOption === key}
                            onChange={() => setSelectedOption(key as ExportOption)}
                        />
                    ))}
                </Form>
                <hr />

                {selectedOption === ExportOption.LOCAL && (
                    <>
                        <Form.Group controlId="annotationsFormat">
                            <Form.Label>Annotations Export Format</Form.Label>
                            <Form.Control
                                as="select"
                                value={annotationsFormat}
                                onChange={(e) => setAnnotationsFormat(e.target.value)}
                            >
                                <option value="GeoJSON">GeoJSON</option>
                            </Form.Control>
                        </Form.Group>
                        <Form.Group controlId="metricsFormat">
                            <Form.Label>Metrics Export Format</Form.Label>
                            <Form.Control
                                as="select"
                                value={metricsFormat}
                                onChange={(e) => setMetricsFormat(e.target.value)}
                            >
                                <option value="Do not export metrics">Do not export metrics</option>
                                <option value="Within GeoJSON properties">Within GeoJSON properties</option>
                                <option value="TSV">TSV</option>
                            </Form.Control>
                        </Form.Group>
                    </>
                )}

                {selectedOption === ExportOption.REMOTE && (
                    <>
                        <Form.Group controlId="savePath">
                            <Form.Label>Save Path</Form.Label>
                            <Form.Control
                                type="text"
                                placeholder="Enter save path (e.g., /data/exports)"
                                value={savePath}
                                onChange={(e) => setSavePath(e.target.value)}
                            />
                        </Form.Group>
                        <Form.Group controlId="annotationsFormat">
                            <Form.Label>Annotations Export Format</Form.Label>
                            <Form.Control
                                as="select"
                                value={annotationsFormat}
                                onChange={(e) => setAnnotationsFormat(e.target.value)}
                            >
                                <option value="GeoJSON">GeoJSON</option>
                            </Form.Control>
                        </Form.Group>
                        <Form.Group controlId="metricsFormat">
                            <Form.Label>Metrics Export Format</Form.Label>
                            <Form.Control
                                as="select"
                                value={metricsFormat}
                                onChange={(e) => setMetricsFormat(e.target.value)}
                            >
                                <option value="Do not export metrics">Do not export metrics</option>
                                <option value="Within GeoJSON properties">Within GeoJSON properties</option>
                                <option value="TSV">TSV</option>
                            </Form.Control>
                        </Form.Group>
                    </>
                )}

                {selectedOption === ExportOption.DSA && (
                    <>
                        <Form.Group controlId="apiKey">
                            <Form.Label>API Key</Form.Label>
                            <Form.Control
                                type="text"
                                placeholder="Enter API key"
                                value={apiKey}
                                onChange={(e) => setApiKey(e.target.value)}
                            />
                        </Form.Group>
                        <Form.Group controlId="collectionName">
                            <Form.Label>Collection Name</Form.Label>
                            <Form.Control
                                type="text"
                                placeholder="Enter collection name"
                                value={collectionName}
                                onChange={(e) => setCollectionName(e.target.value)}
                            />
                        </Form.Group>
                        <Form.Group controlId="folderName">
                            <Form.Label>Folder Name</Form.Label>
                            <Form.Control
                                type="text"
                                placeholder="Enter folder name"
                                value={folderName}
                                onChange={(e) => setFolderName(e.target.value)}
                            />
                        </Form.Group>
                    </>
                )}
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onCancel}>
                    Cancel
                </Button>
                <Button variant="primary" onClick={handleConfirm}>
                    Export
                </Button>
            </Modal.Footer>
        </Modal>
    );
};

export default AnnotationExportModal;