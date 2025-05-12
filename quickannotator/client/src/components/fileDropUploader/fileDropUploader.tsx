
import { useEffect, useState } from "react";
import { UploadedFiles } from "../../types.ts";
import Dropzone from 'react-dropzone';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUp } from 'react-bootstrap-icons';
import { uploadFiles } from '../../helpers/api.ts';
import Button from 'react-bootstrap/Button';
import FileProgressPanel from './fileProgressPanel/fileProgressPanel.tsx'
import './fileDropUploader.css'
import { Prev } from "react-bootstrap/esm/PageItem";

interface Props {
    // gts: Annotation[];
    // setGts: (gts: Annotation[]) => void;
    // currentAnnotation: CurrentAnnotation
}

const accept_file = {
    'application/x-svs': ['.svs', '.ndpi'],
    'application/dicom': ['.dcm'],
    'application/json': ['.json', '.geojson'],
}

const WSIExts = ['svs', 'tif','dcm','vms', 'vmu', 'ndpi',
    'scn', 'mrxs','tiff','svslide','bif','czi']
const JSONExts = ['json','geojosn']


const FileDropUploader = (props: any) => {

    const [files, setFiles] = useState([]);
    const [filesStatus, setFilesStatus] = useState({});


    // remove file form files
    const removeFile = (fileName) => {
        const files_removed = files.filter(f => f.name !== fileName)
        delete filesStatus[fileName]
        setFiles([...files_removed])
        setFilesStatus({ ...filesStatus })
    }
    const handleDone = (e) => {
        e.stopPropagation();
        setFiles([])
        setFilesStatus({})
    }




    // file { file:File, status: Number }
    // status: 0 - selected, 1 - uploading, 2 - uploaded, 3 - error
    const handleDrop = (acceptedFiles) => {


        const newFiles = acceptedFiles.filter((file) => {
            const existingFile = files.find((f) => f.file === file);
            return !existingFile;
        });

        if (newFiles.length > 0) {
            const newFileStatus = {}
            newFiles.forEach(f => {
                newFileStatus[f.name] = { progress: 0, status: 0 }
            });
            setFiles([...files, ...newFiles]);
            setFilesStatus((prev) => ({
                ...prev,
                ...newFileStatus
            }));
        }
    };
    
    const filterByExtensions = (files, exts) => {
        const regex = new RegExp(`\\.(${exts.join('|')})$`, 'i');
        return files.filter(file => regex.test(file));
    }
    const fileNameVerify = () => {
        // const WSIFiles = filterByExts(files, WSIExts)
        // const annotFiles = filterByExts(files, JSONExts)
        // console.log(WSIFiles)
        // console.log(annotFiles)

        // annotFiles = files.filter()
    }

    const handleUpload = async (e) => {
        e.stopPropagation();
        // TODO verify by file name
        // fileNameVerify()

        files.forEach((d) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', d);
            formData.append('project_id',props.project_id)
            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable && filesStatus[d.name]) {
                    const newStatus = {}
                    newStatus[d.name] = { progress: Math.round((event.loaded / event.total) * 100), status: 1 }
                    // const newStatus = {d.name: {progress: Math.round((event.loaded / event.total) * 100) ,status:1 }}
                    setFilesStatus((prev) => ({
                        ...prev,
                        ...newStatus
                    }));
                }

            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    if (filesStatus[d.name]) {
                        const newStatus = {}
                        newStatus[d.name] = { progress: 100, status: 2 }
                        setFilesStatus((prev) => ({
                            ...prev,
                            ...newStatus
                        }));
                        props.reloadHandler(true)
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

            xhr.open("POST", "http://localhost:5000/api/v1/image/upload/file", true);
            xhr.send(formData);
        });



    }

    const {
        acceptedFiles,
        fileRejections,
        getRootProps,
        getInputProps
    } = useDropzone({
        accept: accept_file
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

        <Dropzone accept={accept_file} onDrop={handleDrop} multiple>
            {({ getRootProps, getInputProps }) => (
                <section style={{ width: '50%' }} {...getRootProps({ className: 'document-uploader upload-info upload-box' })}>
                    <div className="upload-box">

                        <CloudArrowUp />
                        <input {...getInputProps()} />
                        <div>
                            <p>Drag and drop your files here</p>
                            <p>
                                Supported WSI files: .svs, .tif, .dcm, .ndpi, .vms, .vmu, .scn,
                            </p>
                            <p>
                                Supported Annotation files:.json, .geojson
                            </p>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                            {files.length > 0 && Object.entries(filesStatus).every(([fileName,{status}])=>status===0) && <Button variant="primary" onClick={handleUpload}>Upload</Button>}
                            {files.length > 0 && Object.entries(filesStatus).every(([fileName,{status}])=>status===2) && <Button variant="primary" onClick={handleDone}>Done</Button>}
                        </div>
                        <section>
                            {Object.entries(filesStatus).map(([file_name, { progress, status }]) => (
                                <FileProgressPanel key={file_name} name={file_name} status={status} progress={progress} removeHandler={removeFile} />

                            ))}
                        </section>


                    </div>
                </section>
            )}
        </Dropzone>
    )
}

export default FileDropUploader;