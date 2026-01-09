import Card from 'react-bootstrap/Card';
import { useEffect } from "react";
import { Button, ListGroup } from "react-bootstrap";
import { AnnotationClass } from "../types.ts";
import { Plus, Pencil, Trash } from 'react-bootstrap-icons';
import { MODAL_DATA, MASK_CLASS_ID } from '../helpers/config.tsx';

interface Props {
    currentAnnotationClass: AnnotationClass | null;
    setcurrentAnnotationClass: (currentAnnotationClass: AnnotationClass) => void;
    setActiveModal: (activeModal: number | null) => void;
    annotationClasses: AnnotationClass[];
    setAnnotationClasses: (classes: AnnotationClass[]) => void;
}

const ClassesPane = (props: Props) => {
    return (
        <Card>
            <Card.Header as={'h5'} className='d-flex justify-content-between align-items-center'>
                Annotation Classes
                <Button variant="secondary" className='btn btn-primary btn-sm'>
                    <Plus onClick={() => props.setActiveModal(MODAL_DATA.ADD_CLASS.id)}/>
                </Button>
            </Card.Header>
            <Card.Body>
                <ListGroup 
                    defaultActiveKey={props.currentAnnotationClass?.id} 
                    style={{ maxHeight: '300px', overflowY: 'auto' }}
                >
                    {props.annotationClasses.map((c) => {
                            return (
                                <ListGroup.Item 
                                    key={c.id}
                                    action 
                                    onClick={() => {
                                        if (props.currentAnnotationClass?.id === MASK_CLASS_ID) {
                                            if (!window.confirm('Reminder: Have you added tissue mask polygons? If not, please do so before annotating other classes. Press OK to continue or Cancel to abort.')) {
                                                return;
                                            }
                                        }
                                        props.setcurrentAnnotationClass(c);
                                    }}
                                    active={props.currentAnnotationClass?.id === c.id}
                                    className="d-flex justify-content-between align-items-center list-group-item-secondary"
                                >
                                    <span>{c.name}</span>
                                    <div>
                                        {c.id !== MASK_CLASS_ID && c.id === props.currentAnnotationClass?.id && (
                                            <Button 
                                                variant="outline-danger" 
                                                size="sm"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    props.setActiveModal(MODAL_DATA.DELETE_CLASS.id);
                                                }}
                                            >
                                                <Trash />
                                            </Button>
                                        )}
                                        <Button 
                                            disabled 
                                            size="lg" 
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