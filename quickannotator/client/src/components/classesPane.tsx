import Card from 'react-bootstrap/Card';
import { useEffect } from "react";
import { Button, ListGroup } from "react-bootstrap";
import { AnnotationClass } from "../types.ts";
import { Plus } from 'react-bootstrap-icons';
import { MODAL_DATA } from '../helpers/config.ts';

interface Props {
    currentClass: AnnotationClass | null;
    setCurrentClass: (currentClass: AnnotationClass) => void;
    setActiveModal: (activeModal: number | null) => void;
    classes: AnnotationClass[];
    setClasses: (classes: AnnotationClass[]) => void;
}

const ClassesPane = (props: Props) => {
    return (
        <Card>
            <Card.Header as={'h5'} className='d-flex justify-content-between align-items-center'>
                Classes
                <Button variant="secondary" className='btn btn-primary btn-sm'>
                    <Plus onClick={() => props.setActiveModal(MODAL_DATA.ADD_CLASS.id)}/>
                </Button>
            </Card.Header>
            <Card.Body>
                <ListGroup 
                    defaultActiveKey={props.currentClass?.id} 
                    style={{ maxHeight: '300px', overflowY: 'auto' }}
                >
                    {props.classes.map((c) => {
                            return (
                                <ListGroup.Item 
                                    key={c.id}
                                    action onClick={() => {props.setCurrentClass(c)}}>
                                        <span>{c.name}</span>
                                        <span>Edit button</span>
                                        <span>Delete button</span>
                                </ListGroup.Item>
                            )
                        }
                    )}
                </ListGroup>
            </Card.Body>
        </Card>
    )
}

export default ClassesPane;