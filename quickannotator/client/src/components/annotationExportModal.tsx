import React from "react";
import { Modal, Button, Form, ListGroup } from "react-bootstrap";
import { useForm, FormProvider, useFormContext } from "react-hook-form";
import { MODAL_DATA } from "../helpers/config";
import { exportAnnotationsToServer, exportAnnotationsToDSA } from "../helpers/api";
import { DataItem } from "../types";
import IdNameList from "./IdNameList";

enum ExportOption {
    SERVER=0,
    DSA,
}

enum ExportFormat {
    GEOJSON = "GEOJSON",
    GEOJSON_NO_PROPS = "GEOJSON_NO_PROPS",
    TSV = "TSV",
}

const exportOptionsLabels = {
    [ExportOption.SERVER]: "Save locally",
    [ExportOption.DSA]: "Push to Digital Slide Archive",
};

const listContainerId = "export-selection-container";

const defaultExportFormats = {
    [ExportFormat.GEOJSON]: true,
    [ExportFormat.GEOJSON_NO_PROPS]: false,
    [ExportFormat.TSV]: false,
};

interface Props {
    show: boolean;
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
    images: DataItem[];
    annotationClasses: DataItem[];
}

interface FormValues {
    selectedOption: ExportOption;
    exportFormats: { [key in ExportFormat]: boolean };
    apiKey?: string;
    collectionName?: string;
    folderName?: string;
    apiUrl?: string;
}

const ExportOptions = () => {
    const { register, watch, setValue } = useFormContext<FormValues>();
    const selectedOption = Number(watch("selectedOption"));
    const exportFormats = watch("exportFormats");

    const handleCheckboxChange = (format: ExportFormat) => {
        setValue(`exportFormats.${format}`, !exportFormats[format]);    // TODO: fix this
    };

    return (
        <>
            <Form>
                {Object.entries(exportOptionsLabels).map(([key, value]) => (
                    <Form.Check
                        key={key}
                        type="radio"
                        label={value}
                        id={key}
                        value={key}
                        {...register("selectedOption")}
                        defaultChecked={key === ExportOption.SERVER.toString()}
                    />
                ))}
            </Form>
            <hr />

            {selectedOption === ExportOption.SERVER && (
                <>
                    <Form.Group controlId="exportFormats">
                        <Form.Label>Select Export Formats</Form.Label>
                        {Object.values(ExportFormat).map((format) => (
                            <Form.Check
                                key={format}
                                type="checkbox"
                                label={format}
                                id={`exportFormat-${format}`}
                                checked={exportFormats[format]}
                                onChange={() => handleCheckboxChange(format)}
                            />
                        ))}
                    </Form.Group>
                </>
            )}

            {selectedOption === ExportOption.DSA && (
                <>
                    <Form.Group controlId="apiUrl">
                        <Form.Label>API URL</Form.Label>
                        <Form.Control
                            type="text"
                            placeholder="Enter API URL"
                            {...register("apiUrl")}
                        />
                    </Form.Group>
                    <Form.Group controlId="apiKey">
                        <Form.Label>API Key</Form.Label>
                        <Form.Control
                            type="text"
                            placeholder="Enter API key"
                            {...register("apiKey")}
                        />
                    </Form.Group>
                    <Form.Group controlId="folderName">
                        <Form.Label>Folder ID</Form.Label>
                        <Form.Control
                            type="text"
                            placeholder="Enter folder ID"
                            {...register("folderName")}
                        />
                    </Form.Group>
                </>
            )}
        </>
    );
};

function updateProgressBar(progress: number) {
    console.log(`Progress: ${progress}%`);
}

const AnnotationExportModal = (props: Props) => {
    const methods = useForm<FormValues>({
        defaultValues: {
            selectedOption: ExportOption.SERVER,
            exportFormats: defaultExportFormats,
        },
    });

    const onSubmit = (data: FormValues) => {
        console.log("Exporting with data:", data);
        const imageIds = props.images.filter((item: DataItem) => item.selected).map((item: DataItem) => item.id);
        const annotationClassIds = props.annotationClasses.filter((item: DataItem) => item.selected).map((item: DataItem) => item.id);

        if (imageIds.length === 0) {
            console.error("No images selected for export");
            return;
        }
        if (annotationClassIds.length === 0) {
            console.error("No annotation classes selected for export");
            return;
        }

        const selectedFormats = Object.entries(data.exportFormats)
            .filter(([_, isSelected]) => isSelected)
            .map(([format]) => format as ExportFormat);

        if (selectedFormats.length === 0) {
            console.error("No export formats selected");
            return;
        }

        switch (Number(data.selectedOption)) {
            case ExportOption.SERVER:
                exportAnnotationsToServer(imageIds, annotationClassIds, selectedFormats)
                    .then(() => console.log("Export to server successful"))
                    .catch((error) => console.error("Export to server failed:", error));
                break;

            case ExportOption.DSA:
                if (!data.apiUrl || !data.apiKey || !data.folderName) {
                    console.error("Missing required fields for DSA export");
                    return;
                }
                exportAnnotationsToDSA(
                    imageIds,
                    annotationClassIds,
                    data.apiUrl,
                    data.apiKey,
                    data.folderName
                )
                    .then(() => console.log("Export to DSA successful"))
                    .catch((error) => console.error("Export to DSA failed:", error));
                break;

            default:
                console.error("Unknown export option:", data.selectedOption);
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
                <div id={`${listContainerId}-images`}>
                    <h5>Image List</h5> {/* Added title for the Image List */}
                    <IdNameList items={props.images} containerId={`${listContainerId}-images`} />
                </div>
                <hr />
                <div id={`${listContainerId}-classes`}>
                    <h5>Annotation Class List</h5> {/* Added title for the Annotation Class List */}
                    <IdNameList items={props.annotationClasses} containerId={`${listContainerId}-classes`} />
                </div>
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