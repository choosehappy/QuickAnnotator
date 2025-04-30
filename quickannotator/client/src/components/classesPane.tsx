import Card from 'react-bootstrap/Card';
import { useEffect } from "react";
import { Button, ListGroup } from "react-bootstrap";
import { AnnotationClass } from "../types.ts";
import { Plus, Pencil, Trash } from 'react-bootstrap-icons';
import { MODAL_DATA } from '../helpers/config.ts';

interface Props {
    currentAnnotationClass: AnnotationClass | null;
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
                    defaultActiveKey={props.currentAnnotationClass?.id} 
                    style={{ maxHeight: '300px', overflowY: 'auto' }}
                >
                    {props.classes.map((c) => {
                            return (
                                <ListGroup.Item 
                                    key={c.id}
                                    action 
                                    onClick={() => {props.setCurrentClass(c)}}
                                    active={props.currentAnnotationClass?.id === c.id}
                                    className="d-flex justify-content-between align-items-center list-group-item-secondary"
                                >
                                    <span>{c.name}</span>
                                    <div>
                                        <Button 
                                            variant="outline-primary" 
                                            size="sm" 
                                            className="me-2"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                // Handle edit logic here
                                            }}
                                        >
                                            <Pencil />
                                        </Button>
                                        <Button 
                                            variant="outline-danger" 
                                            size="sm"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                // Handle delete logic here
                                            }}
                                        >
                                            <Trash />
                                        </Button>
                                        <Button 
                                            disabled 
                                            size="sm" 
                                            style={{ backgroundColor: c.color, border: 'none' }}
                                            className="ms-2"
                                        >
                                        </Button>
                                    </div>
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