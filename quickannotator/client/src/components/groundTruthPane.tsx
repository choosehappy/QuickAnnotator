import Card from 'react-bootstrap/Card';
import AnnotationList from "./annotationList.tsx";


const GroundTruthPane = () => {
    return (
        <Card>
            <Card.Header as={'h5'}>Ground Truths</Card.Header>
            <Card.Body style={{overflow: 'hidden'}}>
                <AnnotationList />
            </Card.Body>
        </Card>
    )
}

export default GroundTruthPane;