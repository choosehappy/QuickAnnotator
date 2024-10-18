import Card from 'react-bootstrap/Card';
import AnnotationList from "./annotationList.tsx";
import Annotation from "../types/annotations.ts";

interface Props {
    preds: Annotation[];
    setPreds: (gts: Annotation[]) => void;
}
const PredictionsPane = (props: Props) => {
    const id = 'id'
    return (
        <Card>
            <Card.Header as={'h5'}>Predictions</Card.Header>
            <Card.Body id={id}>
                <AnnotationList containerId={id} annotations={props.preds}/>
            </Card.Body>
        </Card>
    )
}

export default PredictionsPane;