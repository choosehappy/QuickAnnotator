import ProgressBar from 'react-bootstrap/ProgressBar';
import './fileProgressPanel.css'
import { FileEarmarkText, FileEarmarkImage, Check, X } from 'react-bootstrap-icons';

interface Props {
    name: string
    status: number
    progress: number
    removeHandler: (file_name: string) => void;
}
// status -> 0 - selected, 1 - uploading, 2 - done
interface Props {
    // gts: Annotation[];
    // setGts: (gts: Annotation[]) => void;
    // currentAnnotation: CurrentAnnotation
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
                        {props.status === 0 ? (
                            <X onClick={(e) => {
                                e.stopPropagation();
                                props.removeHandler(props.name)
                            }} />
                            ): props.status === 1 ? (
                                `${props.progress}%`
                            ) : <Check onClick={(e) => {e.stopPropagation();}}/>}
                    </div>
                    

                </div>
            </div>
        </>
    )
}

export default FileProgressPanel;