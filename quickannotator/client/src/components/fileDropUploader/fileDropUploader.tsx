
import { useEffect, useState } from "react";
import {UploadedFiles} from "../../types.ts";
import Dropzone from 'react-dropzone';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUp } from 'react-bootstrap-icons';
import { uploadFiles } from '../../helpers/api.ts';
import './fileDropUploader.css'

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


const FileDropUploader = (props: any) => {

    const [files, setFiles] = useState([]);
    const handleDrop = (acceptedFiles) => {
        const newFiles = acceptedFiles.filter((file) => {
            const existingFile = files.find((f) => f.name === file.name&&f.path === file.path&&f.size === file.size&&f.type === file.type);
            return !existingFile;
        });
        if (newFiles.length > 0) {
            setFiles([...files, ...newFiles]);
        }
    };
    const handleUpload = async (e) => {
        e.stopPropagation();
        const formData = new FormData();

        files.forEach((file) => {
            formData.append('files', file);
        });

        try {
            const response = await fetch('http://localhost:5000/api/v1/image/upload/files', {
                mode: "no-cors",
                method: 'POST',
                body: formData,
            });

            console.log(response)

            // Handle successful upload
            console.log('Files uploaded successfully');
            setFiles([]); // Reset files after successful upload
        } catch (error) {
            console.error('Error uploading files:', error);
        }
    };

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
                    <section style={{ width: '50%' }} {...getRootProps({className: 'document-uploader upload-info upload-box'})}>
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
                        <button onClick={handleUpload} disabled={files.length === 0}>
                                Upload
                        </button>
                        <ul>
                            {files.map((file) => (
                                <li key={file.name}>{file.name}</li>
                            ))}
                        </ul>
                    
                    </div>
                    </section>
                )}
            </Dropzone>
    )
}

export default FileDropUploader;