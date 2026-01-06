import Card from 'react-bootstrap/Card';
import AnnotationList from "./annotationList.tsx";
import { Annotation, AnnotationClass, CurrentAnnotation } from "../types.ts";
import { MODAL_DATA } from '../helpers/config.tsx';

interface Props {
    gts: Annotation[];
    setGts: (gts: Annotation[]) => void;
    currentAnnotation: CurrentAnnotation | null;
    setCurrentAnnotation: React.Dispatch<React.SetStateAction<CurrentAnnotation | null>>;
    annotationClasses: AnnotationClass[];
    setActiveModal: React.Dispatch<React.SetStateAction<number | null>>;
    gtLayerVisible: boolean; // Added prop for layer visibility
}
const GroundTruthPane = (props: Props) => {
    const id = 'gt'; // hardcoded ids should ideally not be used.

    return (
        <Card>
            <Card.Header as={'h5'} className="d-flex justify-content-between align-items-center">
                Ground Truths
                <button 
                    className="btn btn-primary btn-sm" 
                    onClick={() => props.setActiveModal(MODAL_DATA.EXPORT_CONF.id)}
                >
                    Export
                </button>
            </Card.Header>
            {props.gtLayerVisible && ( // Conditionally render Card.Body
                <Card.Body id={id}>
                    <AnnotationList containerId={id} 
                                    annotations={props.gts} 
                                    currentAnnotation={props.currentAnnotation} 
                                    setCurrentAnnotation={props.setCurrentAnnotation}
                                    annotationClasses={props.annotationClasses}
                                    />
                </Card.Body>
            )}
        </Card>
    )
}

export default GroundTruthPane;