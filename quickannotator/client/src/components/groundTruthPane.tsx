import Card from 'react-bootstrap/Card';
import Example1 from "./annotationList.tsx";


const GroundTruthPane = () => {
    return (
        <Card>
            <Card.Header as={'h5'}>Ground Truths</Card.Header>
            <Card.Body>
                <Example1/>
            </Card.Body>
        </Card>
    )
}

export default GroundTruthPane;