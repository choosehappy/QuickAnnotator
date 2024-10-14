import Card from 'react-bootstrap/Card';
import AnnotationList from "./annotationList.tsx";


const PredictionsPane = () => {
    return (
        <Card>
            <Card.Header as={'h5'}>Predictions</Card.Header>
            <Card.Body style={{overflow: 'hidden'}}>
                <AnnotationList />
            </Card.Body>
        </Card>
    )
}

export default PredictionsPane;