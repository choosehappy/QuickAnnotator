
import {useState, useEffect } from "react";
import {Link, useOutletContext} from 'react-router-dom';
import { OutletContextType } from "../types.ts";
import { Plus, PencilSquare, Trash } from 'react-bootstrap-icons';
import { Alert, Container, Row, Col, Card, ButtonToolbar, ButtonGroup, Button } from "react-bootstrap";
import ProjectTable from '../components/projectTable/projectTable.tsx';
import ConfigModal from '../components/modals/project/configModal/configModal.tsx';
import DeleteModal from '../components/modals/project/deleteModal/deleteModal.tsx';
import { Project } from "../types.ts";
import { fetchAllProjects, createProject, updateProject, removeProject } from "../helpers/api.ts"
import {PROJECT_MODAL_STATUS} from '../helpers/config.ts'
const LandingPage = () => {
    // 0 - create, 1 - update, 2 - remove 
    const [modalStatus, setModalStatus] = useState<PROJECT_MODAL_STATUS.CREATE | PROJECT_MODAL_STATUS.REMOVE | PROJECT_MODAL_STATUS.UPDATE | undefined>(undefined)
    const { setCurrentImage, setCurrentProject } = useOutletContext<OutletContextType>();
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

    useEffect(() => {
        setCurrentProject(null)
        setCurrentImage(null);
    }, []);

    const reloadProjects = () => {
        fetchAllProjects().then((resp) => {
            if (resp.status === 200) {
                setProjects(resp.data);
            } else {
                console.error("fetch project error")
            }
        });
    }

    const closeModalHandle = () => {
        setModalStatus(undefined)
    }

    const showDeleteModalHandle = (data) => {
        setDeletedId(data.id)
        setModalStatus(PROJECT_MODAL_STATUS.REMOVE)
    }
    const showConfigModalHandle = (data) => {
        setSelectedProject(data)
        data?setModalStatus(PROJECT_MODAL_STATUS.UPDATE):setModalStatus(PROJECT_MODAL_STATUS.CREATE)
        
    }

    const deleteProject = async () => {
        const rs = await removeProject(deletedId)
        setModalStatus(undefined)
        reloadProjects()
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
                    setModalStatus(undefined)
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
                    setModalStatus(undefined)
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
            <ConfigModal show={(modalStatus == 0 || modalStatus == 1)} status={modalStatus} data={selectedProject} closeHandle={closeModalHandle} submitHandle={createOrUpdateProject} />
            {/* delete project modal */}
            <DeleteModal show={modalStatus == 2} closeHandle={closeModalHandle} submitHandle={deleteProject}/>



        </>
    )
}


export default LandingPage