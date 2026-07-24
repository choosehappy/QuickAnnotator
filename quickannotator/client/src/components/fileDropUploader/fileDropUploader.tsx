import { useEffect, useState, useRef } from "react";
import { UploadStatus, UploadFileStore } from "../../types.ts";
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

import {UPLOAD_ACCEPTED_FILES, WSI_EXTS, JSON_EXTS, TABULAR_EXTS, POLLING_INTERVAL_MS, TASK_STATE} from '../../helpers/config.tsx'
import { FileWithPath } from 'react-dropzone';
import { toast } from "react-toastify";
import TaskChildrenGrid from '../taskChildren/taskChildrenGrid.tsx';
import { Modal, Button as ModalButton } from 'react-bootstrap';
interface Props {

}

interface TaggedFile {
    file: FileWithPath;
    folder_name: string | null;
}

const FileDropUploader = (props: any) => {

    const [files, setFiles] = useState<TaggedFile[]>([]);
    const [filesStatus, setFilesStatus] = useState<UploadFileStore>({});
    // store interval ids for polling ray tasks: taskId -> intervalId
    const intervalsRef = useRef<Record<string, number>>({});
    const [showFolderConfirm, setShowFolderConfirm] = useState(false);
    const [pendingFolderFiles, setPendingFolderFiles] = useState<FileWithPath[]>([]);

    // clear any running pollers on unmount
    useEffect(() => {
        return () => {
            Object.values(intervalsRef.current).forEach((id) => clearInterval(id));
            intervalsRef.current = {};
        };
    }, []);


    // remove file form files
    function removeFile(fileName: string) {
        const files_removed = files.filter(f => f.file.name !== fileName)
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

    function addNewFiles(newFiles: TaggedFile[]) {
        const newFileStatus: UploadFileStore = {}
        newFiles.forEach(f => {
            newFileStatus[f.file.name] = { progress: 0, status: UploadStatus.selected }
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

    function extractFolderName(file: FileWithPath): string | null {
        const webkitPath = (file as any).webkitRelativePath;
        if (webkitPath) {
            const parts = webkitPath.split('/').filter(Boolean);
            if (parts.length > 1) {
                return parts[0];
            }
        }

        // react-dropzone (drag-and-drop) sets `.path`, not `.webkitRelativePath`
        const relPath = (file as any).path;
        if (relPath) {
            const parts = relPath.split('/').filter(Boolean);
            if (parts.length > 1) {
                return parts[0];
            }
        }

        return null;
    }

    function handleFolderConfirm() {
        const taggedFiles: TaggedFile[] = pendingFolderFiles.map(f => ({
            file: f,
            folder_name: extractFolderName(f)
        }));
        addNewFiles(taggedFiles);
        setShowFolderConfirm(false);
        setPendingFolderFiles([]);
    }

    function handleFolderCancel() {
        setShowFolderConfirm(false);
        setPendingFolderFiles([]);
    }

    function handleDrop(acceptedFiles: FileWithPath[], fileRejections: any[]) {
        const folderMap = new Map<string, FileWithPath[]>();
        const regularFiles: FileWithPath[] = [];
        const rejectedFolderFiles: FileWithPath[] = [];

        for (const file of acceptedFiles) {
            const folderName = extractFolderName(file);
            if (folderName) {
                if (!folderMap.has(folderName)) {
                    folderMap.set(folderName, []);
                }
                folderMap.get(folderName)!.push(file);
            } else {
                regularFiles.push(file);
            }
        }

        for (const rejection of fileRejections) {
            const file = rejection.file as FileWithPath;
            const folderName = extractFolderName(file);
            if (folderName) {
                rejectedFolderFiles.push(file);
            }
        }

        if (rejectedFolderFiles.length > 0) {
            for (const file of rejectedFolderFiles) {
                const folderName = extractFolderName(file)!;
                if (!folderMap.has(folderName)) {
                    folderMap.set(folderName, []);
                }
                folderMap.get(folderName)!.push(file);
            }
        }

        if (folderMap.size > 0) {
            const allFolderFiles: FileWithPath[] = [];
            for (const files of folderMap.values()) {
                allFolderFiles.push(...files);
            }
            setPendingFolderFiles(allFolderFiles);
            setShowFolderConfirm(true);
        }

        if (regularFiles.length > 0) {
            const taggedFiles: TaggedFile[] = regularFiles.map(f => ({
                file: f,
                folder_name: null
            }));
            const existingNames = new Set(files.map(f => f.file.name));
            const filteredFiles = taggedFiles.filter(tf => !existingNames.has(tf.file.name));
            if (filteredFiles.length > 0) {
                addNewFiles(filteredFiles);
            }
        }
    }

    const filterByExtensions = (files: FileWithPath[], exts: string[]) => {
        const regex = new RegExp(`\\.(${exts.join('|')})$`, 'i');
        return files.filter((f) => regex.test(f.name));
    }
    const fileNameVerify = () => {
        const WSIFiles = filterByExtensions(files.map(f => f.file), WSI_EXTS)
        const annotFiles = filterByExtensions(files.map(f => f.file), JSON_EXTS)
        const bunchFiles = filterByExtensions(files.map(f => f.file), TABULAR_EXTS)
        return 
    }

    const handleUpload = async (e: any) => {
        e.stopPropagation();

        // Group files by folder_name
        const groups = new Map<string | symbol, TaggedFile[]>();
        const FOLDER_GROUP_PREFIX = 'folder:';
        const NULL_GROUP = Symbol('null_group');

        for (const taggedFile of files) {
            let groupKey: string | symbol;
            if (taggedFile.folder_name) {
                groupKey = FOLDER_GROUP_PREFIX + taggedFile.folder_name;
            } else {
                groupKey = NULL_GROUP;
            }
            if (!groups.has(groupKey)) {
                groups.set(groupKey, []);
            }
            groups.get(groupKey)!.push(taggedFile);
        }

        // Upload each group
        for (const [groupKey, groupFiles] of groups) {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();

            // Add all files in this group
            for (const taggedFile of groupFiles) {
                formData.append('file', taggedFile.file);
            }
            formData.append('project_id', props.project_id);

            // Add folder_name if this is a folder group
            if (groupKey !== NULL_GROUP && groupKey.startsWith(FOLDER_GROUP_PREFIX)) {
                const folderName = groupKey.substring(FOLDER_GROUP_PREFIX.length);
                formData.append('folder_name', folderName);
            }

            // Track total size for progress calculation
            const totalSize = groupFiles.reduce((sum, tf) => sum + tf.file.size, 0);
            let loadedSoFar = 0;

            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const groupProgress = Math.round((event.loaded / event.total) * 100);
                    // Distribute progress across files in the group proportionally
                    let currentLoaded = 0;
                    for (const taggedFile of groupFiles) {
                        const fileProportion = taggedFile.file.size / totalSize;
                        const fileLoaded = Math.round(event.loaded * fileProportion);
                        if (filesStatus[taggedFile.file.name]) {
                            updateFileStatus(taggedFile.file.name, groupProgress, UploadStatus.uploading);
                        }
                    }
                }
            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    const isFolder = groupKey !== NULL_GROUP;
                    const displayName = isFolder ? (groupKey as string).substring(FOLDER_GROUP_PREFIX.length) : groupFiles[0].file.name;

                    if (response.ray_task_id) {
                        const taskId = response.ray_task_id;
                        // Mark all files in group as pending
                        for (const taggedFile of groupFiles) {
                            updateFileStatus(taggedFile.file.name, 100, UploadStatus.pending);
                        }
                        toast(
                            <div>
                                <div>Processing {isFolder ? 'folder' : 'file'} {displayName}</div>
                                <div>
                                    <TaskChildrenGrid parentTaskId={taskId} containerId={`toast-task-${taskId}`} />
                                </div>
                            </div>
                        );

                        const intervalId = window.setInterval(async () => {
                            try {
                                const res = await fetchRayTaskById(taskId);
                                if (res.status === 200 && res.data && res.data.state) {
                                    const state = res.data.state;
                                    if (state === TASK_STATE.FINISHED) {
                                        for (const taggedFile of groupFiles) {
                                            updateFileStatus(taggedFile.file.name, 100, UploadStatus.done);
                                        }
                                        if (props.reloadHandler) props.reloadHandler();
                                        clearInterval(intervalsRef.current[taskId]);
                                        delete intervalsRef.current[taskId];
                                    } else if (state === TASK_STATE.FAILED) {
                                        for (const taggedFile of groupFiles) {
                                            updateFileStatus(taggedFile.file.name, 100, UploadStatus.error);
                                        }
                                        if (props.reloadHandler) props.reloadHandler();
                                        clearInterval(intervalsRef.current[taskId]);
                                        delete intervalsRef.current[taskId];
                                    } else if (state === TASK_STATE.RUNNING) {
                                        console.info(`Ray task ${taskId} is still running...`);
                                    } else {
                                        console.warn(`Unhandled task state: ${state} for task ${taskId}`);
                                    }
                                } else {
                                    console.warn(`Polling ray task ${taskId} returned status ${res.status}`);
                                }
                            } catch (err) {
                                console.error('Error polling ray task:', err);
                            }
                        }, POLLING_INTERVAL_MS);

                        if (intervalsRef.current[taskId]) {
                            clearInterval(intervalsRef.current[taskId]);
                        }
                        intervalsRef.current[taskId] = intervalId;

                    } else {
                        for (const taggedFile of groupFiles) {
                            if (filesStatus[taggedFile.file.name]) {
                                updateFileStatus(taggedFile.file.name, 100, UploadStatus.done);
                            }
                        }
                        if (props.reloadHandler) props.reloadHandler();
                    }

                } else {
                    for (const taggedFile of groupFiles) {
                        console.error(`Error uploading ${taggedFile.file.name}`);
                    }
                }
            };

            xhr.onerror = (e) => {
                console.log(e);
            };

            xhr.open("POST", `..${UploadImageURL()}`, true);
            xhr.send(formData);
        }
    }

    const {
        acceptedFiles,
        fileRejections,
        getRootProps,
        getInputProps
    } = useDropzone({
        getInputProps: () => ({ webkitdirectory: '' }),
        onDrop: handleDrop
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
        <>
            <div style={{ width: '100%' }} {...getRootProps({ className: 'document-uploader upload-info upload-box' })}>
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
                                <p>
                                    Tip: You can also drop entire folders (e.g., DICOM WSI sets).
                                </p>
                            </div>
                        </Col>
                        <Col xs={12} md={6} className="px-0">
                            <ListGroup variant="flush" className="file-list-scroll">
                                {Object.entries(filesStatus).map(([file_name, { progress, status }]) => {
                                    const taggedFile = files.find(f => f.file.name === file_name);
                                    return (
                                        <ListGroup.Item key={file_name} className="p-0 border-0">
                                            <FileProgressPanel 
                                                name={file_name} 
                                                status={status} 
                                                progress={progress} 
                                                removeHandler={removeFile} 
                                                folderName={taggedFile?.folder_name || null} 
                                            />
                                        </ListGroup.Item>
                                    );
                                })}
                            </ListGroup>
                        </Col>
                    </Row>
                </Container>
            </div>

            <Modal show={showFolderConfirm} onHide={handleFolderCancel}>
                <Modal.Header closeButton>
                    <Modal.Title>Confirm Folder Upload</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    Upload DICOM folder containing {pendingFolderFiles.length} files? Only confirm if the folder corresponds to a DICOM Whole Slide Image: https://openslide.org/formats/dicom/.
                </Modal.Body>
                <Modal.Footer>
                    <ModalButton variant="secondary" onClick={handleFolderCancel}>
                        Cancel
                    </ModalButton>
                    <ModalButton variant="primary" onClick={handleFolderConfirm}>
                        Upload
                    </ModalButton>
                </Modal.Footer>
            </Modal>
        </>
    )
}

export default FileDropUploader;