import { useEffect, useState, useRef } from "react";
import { UploadStatus, UploadFileStore, DropzoneFile } from "../../types.ts";
import Dropzone from 'react-dropzone';

import { useDropzone } from 'react-dropzone';
import { CloudArrowUp } from 'react-bootstrap-icons';
import { UploadImageURL, fetchRayTaskById } from '../../helpers/api.ts';
import Button from 'react-bootstrap/Button';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import ListGroup from 'react-bootstrap/ListGroup';
import FileProgressPanel from './fileProgressPanel/fileProgressPanel.tsx'
import './fileDropUploader.css'

import {UPLOAD_ACCEPTED_FILES, WSI_EXTS, JSON_EXTS, TABULAR_EXTS, POLLING_INTERVAL_MS, TASK_STATE} from '../../helpers/config.ts'
import { FileWithPath } from 'react-dropzone';
import { toast } from "react-toastify";
import TaskChildrenGrid from '../taskChildren/taskChildrenGrid.tsx';
interface Props {

}

const FileDropUploader = (props: any) => {

    const [files, setFiles] = useState<FileWithPath[]>([]);
    const [filesStatus, setFilesStatus] = useState<UploadFileStore>({});
    // store interval ids for polling ray tasks: taskId -> intervalId
    const intervalsRef = useRef<Record<string, number>>({});

    // clear any running pollers on unmount
    useEffect(() => {
        return () => {
            Object.values(intervalsRef.current).forEach((id) => clearInterval(id));
            intervalsRef.current = {};
        };
    }, []);


    // remove file form files
    function removeFile(fileName: string) {
        const files_removed = files.filter(f => f.name !== fileName)
        delete filesStatus[fileName];
        setFiles([...files_removed])
        setFilesStatus({ ...filesStatus })
    }

    function updateFileStatus(fileName: string, progress: number, status: UploadStatus) {
        const newStatus: UploadFileStore = {}
        if (filesStatus[fileName]) {
            newStatus[fileName] = { progress: progress, status: status };
        } else {
            console.error(`File ${fileName} not found in status store.`);
            return;
        }
        setFilesStatus((prev) => ({
            ...prev,
            ...newStatus
        }));
    }

    function addNewFiles(newFiles: FileWithPath[]) {
        const newFileStatus: UploadFileStore = {}
        newFiles.forEach(f => {
            newFileStatus[f.name] = { progress: 0, status: UploadStatus.selected }
        });
        setFiles([...files, ...newFiles]);
        setFilesStatus((prev) => ({
            ...prev,
            ...newFileStatus
        }));
    }

    function handleDone(e: any) {
        e.stopPropagation();
        setFiles([])
        setFilesStatus({})
    }


    // file { file:File, status: Number }
    // status: 0 - selected, 1 - uploading, 2 - uploaded, 3 - error
    const handleDrop = (acceptedFiles: FileWithPath[]) => {


        const newFiles = acceptedFiles.filter((file) => {
            const existingFile = files.find((f) => f === file);
            return !existingFile;
        });

        if (newFiles.length > 0) {
            addNewFiles(newFiles);
        }
    };

    const filterByExtensions = (files: FileWithPath[], exts: string[]) => {
        const regex = new RegExp(`\\.(${exts.join('|')})$`, 'i');
        return files.filter((f) => regex.test(f.name));
    }
    const fileNameVerify = () => {
        const WSIFiles = filterByExtensions(files, WSI_EXTS)
        const annotFiles = filterByExtensions(files, JSON_EXTS)
        const bunchFiles = filterByExtensions(files, TABULAR_EXTS)
        return 
    }

    const handleUpload = async (e: any) => {
        e.stopPropagation();
        // TODO verify by file name
        // if(fileNameVerify()) {
        //     console.error('Tthe format is not supported!')
        // }

        files.forEach((d) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', d);
            formData.append('project_id',props.project_id)
            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable && filesStatus[d.name]) {
                    updateFileStatus(d.name, Math.round((event.loaded / event.total) * 100), UploadStatus.uploading)
                }

            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);

                    if (response.ray_task_id) {
                        const taskId = response.ray_task_id;
                        updateFileStatus(d.name, 100, UploadStatus.pending);
                        toast(
                            <div>
                                <div>Processing File {d.name}</div>
                                <div>
                                    <TaskChildrenGrid parentTaskId={taskId} containerId={`toast-task-${taskId}`} />
                                </div>
                            </div>
                        );

                        // start polling the ray task status every 5 seconds until finished
                        const intervalId = window.setInterval(async () => {
                            try {
                                const res = await fetchRayTaskById(taskId);
                                if (res.status === 200 && res.data && res.data.state) {
                                    const state = res.data.state;
                                    // When Ray reports the task finished, mark upload done and stop polling
                                    if (state === TASK_STATE.FINISHED) {
                                        updateFileStatus(d.name, 100, UploadStatus.done);
                                        if (props.reloadHandler) props.reloadHandler();
                                        // clear this interval
                                        clearInterval(intervalsRef.current[taskId]);
                                        delete intervalsRef.current[taskId];
                                    } else if (state === TASK_STATE.FAILED) {
                                        updateFileStatus(d.name, 100, UploadStatus.error);
                                        if (props.reloadHandler) props.reloadHandler();
                                        // clear this interval
                                        clearInterval(intervalsRef.current[taskId]);
                                        delete intervalsRef.current[taskId];
                                    } else if (state === TASK_STATE.RUNNING) {
                                        console.info(`Ray task ${taskId} is still running...`);
                                    } else {
                                        console.warn(`Unhandled task state: ${state} for task ${taskId}`);
                                    }
                                } else {
                                    // if task not found or error, keep pending but log
                                    console.warn(`Polling ray task ${taskId} returned status ${res.status}`);
                                }
                            } catch (err) {
                                console.error('Error polling ray task:', err);
                            }
                        }, POLLING_INTERVAL_MS);

                        // store interval id so we can clear later
                        intervalsRef.current[taskId] = intervalId as unknown as number;

                    } else if (filesStatus[d.name]) {
                        updateFileStatus(d.name, 100, UploadStatus.done);
                        props.reloadHandler();
                    }

                } else {
                    console.error(`Error uploading ${d.name}`);
                }
                // setUploading(false);
            };

            xhr.onerror = (e) => {
                console.log(e)
                // console.error(`Error uploading ${file.name}`);
            };
            console.log()
            xhr.open("POST", `..${UploadImageURL()}`, true);
            xhr.send(formData);
        });



    }

    const {
        acceptedFiles,
        fileRejections,
        getRootProps,
        getInputProps
    } = useDropzone({
        accept: UPLOAD_ACCEPTED_FILES
    });

    const acceptedFileItems = acceptedFiles.map(file => (
        <li key={file.path} >
            {file.path} - {file.size} bytes
        </li>
    ));

    const fileRejectionItems = fileRejections.map(({ file, errors }) => (
        <li key={file.path} >
            {file.path} - {file.size} bytes
            <ul>
                {
                    errors.map(e => (
                        <li key={e.code} > {e.message} </li>
                    ))
                }
            </ul>
        </li>
    ));

    return (

        <Dropzone accept={UPLOAD_ACCEPTED_FILES} onDrop={handleDrop} multiple>
            {({ getRootProps, getInputProps }) => (
                <section style={{ width: '100%' }} {...getRootProps({ className: 'document-uploader upload-info upload-box' })}>
                    <input {...getInputProps()} />
                    <Container fluid className="p-2">
                                <Row>
                                    <Col xs={12} md={6} className="px-0">
                                        <div className="drop-instructions">
                                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                                <CloudArrowUp />
                                                <div style={{ marginLeft: 'auto', display: 'flex', gap: '10px' }}>
                                                    {files.length > 0 && Object.entries(filesStatus).every(([fileName, { status }]) => status === UploadStatus.selected) && (
                                                        <Button variant="primary" onClick={handleUpload}>Upload</Button>
                                                    )}
                                                    {files.length > 0 && Object.entries(filesStatus).every(([fileName, { status }]) => status === UploadStatus.done || status === UploadStatus.error) && (
                                                        <Button variant="primary" onClick={handleDone}>Done</Button>
                                                    )}
                                                </div>
                                            </div>
                                            <p>Drag and drop your files here</p>
                                            <p>
                                                Supported WSI files: {WSI_EXTS.map(ext => `.${ext}`).join(', ')}
                                            </p>
                                            <p>
                                                Supported Annotation files: {JSON_EXTS.map(ext => `.${ext}`).join(', ')}
                                            </p>
                                            <p>
                                                Supported tabular formats for bulk import of slides and annotations: {TABULAR_EXTS.map(ext => `.${ext}`).join(', ')}
                                            </p>
                                        </div>
                                    </Col>
                                    <Col xs={12} md={6} className="px-0">
                                        <ListGroup variant="flush" className="file-list-scroll">
                                            {Object.entries(filesStatus).map(([file_name, { progress, status }]) => (
                                                <ListGroup.Item key={file_name} className="p-0 border-0">
                                                    <FileProgressPanel name={file_name} status={status} progress={progress} removeHandler={removeFile} />
                                                </ListGroup.Item>
                                            ))}
                                        </ListGroup>
                                    </Col>
                                </Row>
                </Container>
                </section>
            )}
        </Dropzone>
    )
}

export default FileDropUploader;