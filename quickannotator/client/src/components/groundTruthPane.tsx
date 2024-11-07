import Card from 'react-bootstrap/Card';
import AnnotationList from "./annotationList.tsx";
import { Annotation } from "../types.ts"

interface Props {
    gts: Annotation[];
    setGts: (gts: Annotation[]) => void;
}
const GroundTruthPane = (props: Props) => {
    const id = 'gt'; // hardcoded ids should ideally not be used.

    return (
        <Card>
            <Card.Header as={'h5'}>Ground Truths</Card.Header>
            <Card.Body id={id}>
                <AnnotationList containerId={id} annotations={props.gts}/>
            </Card.Body>
        </Card>
    )
}

export default GroundTruthPane;