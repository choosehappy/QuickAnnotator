import React from "react";
import { Modal, Button, Form } from "react-bootstrap";
import { useForm, FormProvider, useFormContext } from "react-hook-form";
import { MODAL_DATA } from "../helpers/config";
import { downloadAnnotations } from "../helpers/api";

enum ExportOption {
    LOCAL = 0,
    REMOTE,
    DSA,
}

enum ExportFormat {
    GEOJSON = "GeoJSON",
    GEOJSON_NO_PROPS = "GeoJSON (no properties)",
}

enum MetricsFormat {
    TSV = "TSV",
    DO_NOT_EXPORT = "Do not export",
}

const exportOptionsLabels = {
    [ExportOption.LOCAL]: "Save locally",
    [ExportOption.REMOTE]: "Save remotely",
    [ExportOption.DSA]: "Push to Digital Slide Archive",
};

const savePathPlaceholder = "Default: data/{project_id}/{image_id}/{}";

interface Props {
    show: boolean;
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
}

interface FormValues {
    selectedOption: ExportOption;
    annotationsFormat: ExportFormat;
    propsFormat: MetricsFormat;
    savePath?: string;
    apiKey?: string;
    collectionName?: string;
    folderName?: string;
}

const ExportOptions = () => {
    const { register, watch } = useFormContext<FormValues>();
    const selectedOption = Number(watch("selectedOption"));

    // Debugging log to check the value of selectedOption
    console.log("Selected Option:", selectedOption);

    return (
        <>
            <Form>
                {Object.entries(exportOptionsLabels).map(([key, value]) => {

                    return (
                        <Form.Check
                            key={key}
                            type="radio"
                            label={value}
                            id={key}
                            value={key} // Ensure this matches the enum values
                            {...register("selectedOption")}
                            defaultChecked={key === ExportOption.LOCAL.toString()}
                        />
                    );
                })}
            </Form>
            <hr />

            {selectedOption === ExportOption.LOCAL && (
                <>
                    <Form.Group controlId="annotationsFormat">
                        <Form.Label>Annotations Export Format</Form.Label>
                        <Form.Control as="select" {...register("annotationsFormat")}>
                            {Object.values(ExportFormat).map((format) => (
                                <option key={format} value={format}>
                                    {format}
                                </option>
                            ))}
                        </Form.Control>
                    </Form.Group>
                    <Form.Group controlId="metricsFormat">
                        <Form.Label>Metrics Export Format</Form.Label>
                        <Form.Control as="select" {...register("propsFormat")}>
                            {Object.values(MetricsFormat).map((format) => (
                                <option key={format} value={format}>
                                    {format}
                                </option>
                            ))}
                        </Form.Control>
                    </Form.Group>
                </>
            )}

            {selectedOption === ExportOption.REMOTE && (
                <>
                    <Form.Group controlId="annotationsFormat">
                        <Form.Label>Annotations Export Format</Form.Label>
                        <Form.Control as="select" {...register("annotationsFormat")}>
                            {Object.values(ExportFormat).map((format) => (
                                <option key={format} value={format}>
                                    {format}
                                </option>
                            ))}
                        </Form.Control>
                    </Form.Group>
                    <Form.Group controlId="metricsFormat">
                        <Form.Label>Metrics Export Format</Form.Label>
                        <Form.Control as="select" {...register("propsFormat")}>
                            {Object.values(MetricsFormat).map((format) => (
                                <option key={format} value={format}>
                                    {format}
                                </option>
                            ))}
                        </Form.Control>
                    </Form.Group>
                    <Form.Group controlId="savePath">
                        <Form.Label>Save Path</Form.Label>
                        <Form.Control
                            type="text"
                            placeholder={savePathPlaceholder}
                            {...register("savePath")}
                        />
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
                            {...register("apiKey")}
                        />
                    </Form.Group>
                    <Form.Group controlId="collectionName">
                        <Form.Label>Collection Name</Form.Label>
                        <Form.Control
                            type="text"
                            placeholder="Enter collection name"
                            {...register("collectionName")}
                        />
                    </Form.Group>
                    <Form.Group controlId="folderName">
                        <Form.Label>Folder Name</Form.Label>
                        <Form.Control
                            type="text"
                            placeholder="Enter folder name"
                            {...register("folderName")}
                        />
                    </Form.Group>
                </>
            )}
        </>
    );
};

const AnnotationExportModal = (props: Props) => {
    const methods = useForm<FormValues>({
        defaultValues: {
            selectedOption: ExportOption.LOCAL,
            annotationsFormat: ExportFormat.GEOJSON,
            propsFormat: MetricsFormat.DO_NOT_EXPORT,
        },
    });

    const onSubmit = (data: FormValues) => {
        console.log("Exporting with data:", data);
        if (data.selectedOption === ExportOption.LOCAL) {
            downloadAnnotations([1], [1])
                .then(() => console.log("Download successful"))
                .catch((error) => console.error("Download failed:", error));
        } else if (data.selectedOption === ExportOption.REMOTE) {
            console.log("Exporting remotely with data:", data);
        } else if (data.selectedOption === ExportOption.DSA) {
            console.log("Exporting to DSA with data:", data);
        }
    };

    const onCancel = () => {
        props.setActiveModal(null);
        methods.reset();
    };

    return (
        <Modal show={props.show} onHide={onCancel}>
            <Modal.Header closeButton>
                <Modal.Title>{MODAL_DATA.EXPORT_CONF.title}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <p>{MODAL_DATA.EXPORT_CONF.description}</p>
                <hr />
                <FormProvider {...methods}>
                    <form onSubmit={methods.handleSubmit(onSubmit)}>
                        <ExportOptions />
                        <Modal.Footer>
                            <Button variant="secondary" onClick={onCancel}>
                                Cancel
                            </Button>
                            <Button variant="primary" type="submit">
                                Export
                            </Button>
                        </Modal.Footer>
                    </form>
                </FormProvider>
            </Modal.Body>
        </Modal>
    );
};

export default AnnotationExportModal;