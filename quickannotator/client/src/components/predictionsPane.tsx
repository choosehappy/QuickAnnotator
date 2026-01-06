import Card from 'react-bootstrap/Card';
import AnnotationList from "./annotationList.tsx";
import { Annotation, AnnotationClass, CurrentAnnotation } from "../types.ts";

interface Props {
    preds: Annotation[];
    setPreds: React.Dispatch<React.SetStateAction<Annotation[] | null>>;
    selectedPred: CurrentAnnotation | null;
    setSelectedPred: React.Dispatch<React.SetStateAction<CurrentAnnotation | null>>;
    annotationClasses: AnnotationClass[];
    predLayerVisible: boolean; // Added prop for layer visibility
}
const PredictionsPane = (props: Props) => {
    const id = 'id';
    return (
        <Card>
            <Card.Header as={'h5'}>
                Predictions ({props.predLayerVisible ? props.preds.length : 0})
            </Card.Header>
            {props.predLayerVisible && ( // Conditionally render Card.Body
                <Card.Body id={id}>
                    <AnnotationList containerId={id} 
                                    annotations={props.preds} 
                                    annotationClasses={props.annotationClasses}
                                    currentAnnotation={props.selectedPred}
                                    setCurrentAnnotation={props.setSelectedPred}
                                    />
                </Card.Body>
            )}
        </Card>
    )
}

export default PredictionsPane;