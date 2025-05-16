import { Link, useOutletContext } from 'react-router-dom';
import { useRef, useState, useEffect, createElement } from "react";
import { Plus, PencilSquare, Trash } from 'react-bootstrap-icons';
import { Alert, Form, Modal, Container, Row, Col, Card, ButtonToolbar, ButtonGroup, Button } from "react-bootstrap";
import ProjectTable from '../components/projectTable/projectTable.tsx';
import { Project } from "../types.ts";
import { fetchAllProjects, createProject, updateProject, removeProject } from "../helpers/api.ts"
import { PROJECT_EDIT_MODAL_DATA } from "../helpers/config.ts"
const LandingPage = () => {
    const [projectDeleteModalShow, setProjectDeleteModalShow] = useState<boolean>(false)
    const [projectConfigModalShow, setProjectConfigModalShow] = useState<boolean>(false)

    const [projects, setProjects] = useState<Project[]>([])
    const [showAlert, setShowAlert] = useState<boolean>(false)
    const [deletedId, setDeletedId] = useState<number | undefined>(undefined)
    const [selectedProject, setSelectedProject] = useState<Project | undefined>(undefined)

    useEffect(() => {
        fetchAllProjects().then((resp) => {
            if (resp.status === 200) {
                setProjects(resp.data);
            } else {
                console.error("fetch project error")
            }

        });
    }, [])

    const reloadProjects = () => {
        fetchAllProjects().then((resp) => {
            if (resp.status === 200) {
                setProjects(resp.data);
            } else {
                console.error("fetch project error")
            }
        });
    }

    const handleCloseDeleteModal = () => {
        setProjectDeleteModalShow(false)
    }
    const handleCloseConfigModal = () => {
        setProjectConfigModalShow(false)
    }

    const showDeleteModalHandle = (data) => {
        setDeletedId(data.id)
        setProjectDeleteModalShow(true)
    }
    const showConfigModalHandle = (data) => {
        setSelectedProject(data)
        setProjectConfigModalShow(true)
    }

    const deleteProject = async () => {
        const rs = await removeProject(deletedId)
        setProjectDeleteModalShow(false)
        reloadProjects()
        console.log('reload 3')
    }

    const createOrUpdateProject = async (e) => {
        e.preventDefault()
        const formData = new FormData(e.target)
        const formDataObj = Object.fromEntries(formData.entries())
        // formDataObj.is_dataset_large =  false;
        if (selectedProject && selectedProject.id) {
            // update a existing project
            formDataObj.project_id = selectedProject.id
            updateProject(formDataObj).then((resp) => {
                if (resp.status == 200) {
                    setProjectConfigModalShow(false)
                    setSelectedProject(undefined)
                    reloadProjects()
                    console.log('reload 2')
                    // TODO show message                
                } else {
                    console.error("update project failed")
                }

            })
        } else {
            // create a new project
            createProject(formDataObj).then((resp) => {
                if (resp.status == 200) {
                    setProjectConfigModalShow(false)
                    setSelectedProject(undefined)
                    reloadProjects()
                    console.log('reload 1')
                    // TODO show message                
                } else {
                    console.error("create project failed")
                }
            })

        }
    }

    return (
        <>
            {showAlert && <Alert variant="danger" onClose={() => setShowAlert(false)} dismissible>
                <Alert.Heading>Oh snap! You got an error!</Alert.Heading>
            </Alert>}
            <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                <Row className="d-flex">
                    <Col>
                        <nav className="navbar float-end">
                            <ButtonToolbar aria-label="Toolbar with button groups">
                                <ButtonGroup className={"me-2"}>
                                    <Button variant="primary" title="Add New Project" onClick={() => showConfigModalHandle(null)}><Plus /></Button>
                                </ButtonGroup>
                            </ButtonToolbar>
                        </nav>
                    </Col>
                </Row>
                <Row className="d-flex flex-grow-1">
                    <Col className="d-flex flex-grow-1"><Card className="flex-grow-1">
                        <Card.Body>
                            <ProjectTable containerId='project_table' projects={projects} deleteHandle={showDeleteModalHandle} editHandle={showConfigModalHandle} />
                        </Card.Body>
                    </Card></Col>
                </Row>
            </Container>
            {/* delete project modal */}
            <Modal show={projectDeleteModalShow} onHide={handleCloseDeleteModal}>
                <Modal.Header closeButton>
                    {/* <Modal.Title>Are You</Modal.Title> */}
                </Modal.Header>
                <Modal.Body>Are you sure you want to delete this project?</Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={handleCloseDeleteModal}>
                        Cancel
                    </Button>
                    <Button variant="danger" onClick={deleteProject}>
                        Delete
                    </Button>
                </Modal.Footer>
            </Modal>
            {/* create project modal */}
            <Modal show={projectConfigModalShow} onHide={handleCloseConfigModal}>
                <Form onSubmit={createOrUpdateProject}>
                    <Modal.Header closeButton>
                        <Modal.Title>{selectedProject && selectedProject.id ? PROJECT_EDIT_MODAL_DATA.EDIT.title : PROJECT_EDIT_MODAL_DATA.ADD.title}
                        </Modal.Title>
                    </Modal.Header>
                    <Modal.Body>
                        <Form.Text className="text-muted">
                            {selectedProject && selectedProject.id ? PROJECT_EDIT_MODAL_DATA.EDIT.text : PROJECT_EDIT_MODAL_DATA.ADD.text}
                        </Form.Text>
                        <Form.Group className="mb-3">
                            <Form.Label>Name</Form.Label>
                            <Form.Control name="name" type="text" placeholder="Enter Project Name" defaultValue={selectedProject && selectedProject.id ? selectedProject.name : ''} />
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label>Dataset Size</Form.Label>
                            <Form.Select name="is_dataset_large" value={selectedProject && selectedProject.id ? selectedProject.is_dataset_large : false} onChange={(e) => {
                                setSelectedProject({ ...selectedProject, is_dataset_large: e.target.value })
                            }}>
                                <option value="false" >{"< 1000 Whole Slide Images"}</option>
                                <option value="true" >{"> 1000 Whole Slide Images"}</option>
                            </Form.Select>
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label>Description</Form.Label>
                            <Form.Control name="description" as="textarea" placeholder="Enter Project Description" rows={3} defaultValue={selectedProject && selectedProject.id ? selectedProject.description : ''} />
                        </Form.Group>

                    </Modal.Body>
                    <Modal.Footer>
                        <Button variant="secondary" onClick={handleCloseConfigModal}>
                            Cancel
                        </Button>
                        <Button variant="primary" type="submit">
                            {selectedProject && selectedProject.id ? PROJECT_EDIT_MODAL_DATA.EDIT.btnText : PROJECT_EDIT_MODAL_DATA.ADD.btnText}
                        </Button>
                    </Modal.Footer>
                </Form>
            </Modal>

        </>
    )
}


export default LandingPage