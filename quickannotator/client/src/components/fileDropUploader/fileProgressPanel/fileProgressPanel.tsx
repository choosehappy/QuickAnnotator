import ProgressBar from 'react-bootstrap/ProgressBar';
import './fileProgressPanel.css'
import { FileEarmarkText, FileEarmarkImage, Check, X } from 'react-bootstrap-icons';
import { UploadStatus } from '../../../types.ts';
import { Spinner } from 'react-bootstrap';

interface Props {
    name: string
    status: UploadStatus
    progress: number
    removeHandler: (file_name: string) => void;
}

const WSI_FILES_EXT: string[] = ['svs', 'tif', 'dcm', 'ndpi', 'vms', 'vmu', 'scn']

const isWSIFile = (file_name: string) => {
    const file_ext: string | undefined = file_name.split('.').pop();
    if (!file_ext) {
        throw new Error("File extension could not be determined.");
    }
    return WSI_FILES_EXT.includes(file_ext)
}



const FileProgressPanel = (props: Props) => {
    return (
        <>
            <div className="file-card">
                <div className="file-icon">{ isWSIFile(props.name)?<FileEarmarkImage />:<FileEarmarkText />}</div>
                <div className="file-info">
                    <div style={{ flex: 1 }}>
                        <h6>{props.name}</h6>
                        <ProgressBar now={props.progress} label={`${props.progress}%`} />
                    </div>
                    <div className="check-circle">
                        {props.status === UploadStatus.selected ? (
                            <X onClick={(e) => {
                                e.stopPropagation();
                                props.removeHandler(props.name)
                            }} />
                        ) : props.status === UploadStatus.pending ? (
                            <Spinner animation="border" size="sm" role="status">
                                <span className="visually-hidden">Loading...</span>
                            </Spinner>
                        ) : props.status === UploadStatus.error ? (
                            <X className="failure-icon" />
                        ) : (
                            <Check onClick={(e) => { e.stopPropagation(); }} />
                        )}
                    </div>
                    

                </div>
            </div>
        </>
    )
}

export default FileProgressPanel;