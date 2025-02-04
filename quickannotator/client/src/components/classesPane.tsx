import Card from 'react-bootstrap/Card';
import { useEffect, useState } from "react";
import { ListGroup } from "react-bootstrap";
import { AnnotationClass } from "../types.ts";
import { fetchAnnotationClasses, fetchAnnotationClassById } from "../helpers/api.ts";

interface Props {
    currentClass: AnnotationClass | null;
    setCurrentClass: (currentClass: AnnotationClass) => void;
}
const ClassesPane = (props: Props) => {
    const [classes, setClasses] = useState<AnnotationClass[]>([]);
    useEffect(() => {
        fetchAnnotationClasses().then((resp) => {
            setClasses(resp.data);
        })
        fetchAnnotationClassById(2).then((resp) => {
            props.setCurrentClass(resp.data);
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