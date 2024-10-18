import Card from 'react-bootstrap/Card';
import AnnotationClass from "../types/annotationClass.ts";
import {useEffect, useState} from "react";
import {fetchAnnotationClass} from "../helpers/helpers.ts";
import {ListGroup} from "react-bootstrap";

interface Props {
    currentClass: AnnotationClass | null;
    setCurrentClass: (currentClass: AnnotationClass) => void;
}
const ClassesPane = (props: Props) => {
    const [classes, setClasses] = useState<AnnotationClass[]>([]);
    useEffect(() => {
        fetchAnnotationClass().then((resp) => {
            setClasses(resp);
        })
        fetchAnnotationClass(1).then((resp) => {
            props.setCurrentClass(resp);
        });


    }, []);

    return (
        <Card>
            <Card.Header as={'h5'}>Classes</Card.Header>
            <Card.Body>
                <ListGroup>
                    {classes.map((c) => {
                            return (
                                <ListGroup.Item key={c.id} onClick={() => props.setCurrentClass(c)}>{c.name}</ListGroup.Item>
                            )
                        }
                    )}
                </ListGroup>
            </Card.Body>
        </Card>
    )
}

export default ClassesPane;