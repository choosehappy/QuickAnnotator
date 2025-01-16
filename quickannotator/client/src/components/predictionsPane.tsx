import Card from 'react-bootstrap/Card';
import AnnotationList from "./annotationList.tsx";
import { Annotation, CurrentAnnotation } from "../types.ts";

interface Props {
    preds: Annotation[];
    setPreds: (gts: Annotation[]) => void;
    currentAnnotation: React.MutableRefObject<CurrentAnnotation | null>;
}
const PredictionsPane = (props: Props) => {
    const id = 'id'
    return (
        <Card>
            <Card.Header as={'h5'}>Predictions</Card.Header>
            <Card.Body id={id}>
            <AnnotationList containerId={id} 
                                annotations={props.preds} 
                                currentAnnotation={props.currentAnnotation} 
                                />
            </Card.Body>
        </Card>
    )
}

export default PredictionsPane;