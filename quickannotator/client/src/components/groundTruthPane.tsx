import Card from 'react-bootstrap/Card';
import AnnotationList from "./annotationList.tsx";


const GroundTruthPane = () => {
    const id = 'gt'; // hardcoded ids should ideally not be used.
    return (
        <Card>
            <Card.Header as={'h5'}>Ground Truths</Card.Header>
            <Card.Body id={id}>
                <AnnotationList containerId={id}/>
            </Card.Body>
        </Card>
    )
}

export default GroundTruthPane;