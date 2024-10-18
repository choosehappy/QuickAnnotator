import Card from 'react-bootstrap/Card';
import AnnotationList from "./annotationList.tsx";


const PredictionsPane = ({preds, setPreds}) => {
    const id = 'id'
    return (
        <Card>
            <Card.Header as={'h5'}>Predictions</Card.Header>
            <Card.Body id={id}>
                <AnnotationList containerId={id}/>
            </Card.Body>
        </Card>
    )
}

export default PredictionsPane;