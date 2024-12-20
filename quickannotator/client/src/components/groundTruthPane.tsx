import Card from 'react-bootstrap/Card';
import AnnotationList from "./annotationList.tsx";
import { Annotation, CurrentAnnotation } from "../types.ts"
import { propTypes } from 'react-bootstrap/esm/Image';

interface Props {
    gts: Annotation[];
    setGts: (gts: Annotation[]) => void;
    currentAnnotation: React.MutableRefObject<CurrentAnnotation | null>;
}
const GroundTruthPane = (props: Props) => {
    const id = 'gt'; // hardcoded ids should ideally not be used.

    return (
        <Card>
            <Card.Header as={'h5'}>Ground Truths</Card.Header>
            <Card.Body id={id}>
                <AnnotationList containerId={id} 
                                annotations={props.gts} 
                                currentAnnotation={props.currentAnnotation} 
                                />
            </Card.Body>
        </Card>
    )
}

export default GroundTruthPane;