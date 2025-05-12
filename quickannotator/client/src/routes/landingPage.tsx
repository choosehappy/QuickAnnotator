import { Link, useOutletContext } from 'react-router-dom';
import { useRef, useState, useEffect, createElement } from "react";
import { Plus, PencilSquare, Trash } from 'react-bootstrap-icons';

import { Column, GridOption, SlickgridReactInstance, SlickgridReact } from "slickgrid-react";
import { Alert, Form, Modal, Container, Row, Col, Card, ButtonToolbar, ButtonGroup, Button, ListGroup } from "react-bootstrap";
import { Project, OutletContextType } from "../types.ts";
import { fetchAllProjects, createProject, updateProject, removeProject } from "../helpers/api.ts"
const containerId = 'land-page'
const LandingPage = () => {
    const [projectDeleteModalShow, setProjectDeleteModalShow] = useState<boolean>(false)
    const [projectConfigModalShow, setProjectConfigModalShow] = useState<boolean>(false)
    const [isCreateProject, setIsCreateProject] = useState<boolean>(true)

    const [projects, setProjects] = useState<Project[]>([])
    const [reloadProjects, setReloadProjects] = useState<boolean>(false)
    const [showAlert, setShowAlert] = useState<boolean>(false)
    const [deletedId, setDeletedId] = useState<number | undefined>(undefined)
    const [selectedProject, setSelectedProject] = useState<Project | undefined>(undefined)
    // const [reloadProjects, setReloadProjects] = useState<boolean>(false)


    const gridRef = useRef(null);

    const actionFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {
        const delBtn = document.createElement('button');
        delBtn.className = 'btn btn-danger btn-sm project-icon';
        delBtn.textContent = 'delete'
        delBtn.addEventListener('click', (e) => { showDeleteModalHandle(dataContext) })

        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-primary btn-sm project-icon';
        editBtn.textContent = 'edit'
        // const editIcon = document.createElement('PencilSquare');
        // editBtn.appendChild(editIcon)
        editBtn.addEventListener('click', (e) => { showConfigModalHandle(dataContext, false) })

        const div = document.createElement('div');
        div.appendChild(editBtn)
        div.appendChild(delBtn)
        return div
    }
    const nameFormatter = (row: number, cell: number, value: any, columnDef: Column, dataContext: any) => {

        return `<a target="_blank" href="./project/${dataContext.id}">${value}</a>`
    }
    const columns: Column[] = [
        { id: 'id', name: 'Id', field: 'id', sortable: true },
        { id: 'name', name: 'Name', field: 'name', sortable: true, formatter: nameFormatter },
        { id: 'is_dataset_large', name: 'Large Dataset', field: 'is_dataset_large', sortable: true},
        { id: 'description', name: 'Description', field: 'description', sortable: true },
        { id: 'datetime', name: 'Date Time', field: 'datetime', sortable: true },
        { id: 'action', name: '', field: 'action', sortable: true, formatter: actionFormatter }
    ];
    const gridOptions: GridOption = {
        enableAutoResize: true,
        autoHeight: true,
        rowHeight: 64,
        forceFitColumns: true,
        autoResize: {
            container: `#${containerId}-grid`,
        },

    };
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

        if (reloadProjects)
            fetchAllProjects().then((resp) => {
                if (resp.status === 200) {
                    setProjects(resp.data);
                } else {
                    console.error("fetch project error")
                }
            });
    }, [reloadProjects])

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
    const showConfigModalHandle = (data, create = true) => {
        create ? setSelectedProject(undefined) : setSelectedProject(data)
        setIsCreateProject(create)
        setProjectConfigModalShow(true)
    }

const deleteProject = async () => {

    // 
    const rs = await removeProject(deletedId)
    setProjectDeleteModalShow(false)
    setReloadProjects(true)
}
const createOrUpdateProject = async (e) => {
    e.preventDefault()
    const formData = new FormData(e.target)
    const formDataObj = Object.fromEntries(formData.entries())

    formDataObj.is_dataset_large = formDataObj.is_dataset_large !== 'false';
    if (isCreateProject) {
        // create a new project
        createProject(formDataObj).then((resp) => {
            setProjectConfigModalShow(false)
            setReloadProjects(true)
            // TODO show message
        })
    } else {
        // update a existing project
        formDataObj.project_id = selectedProject.id
        updateProject(formDataObj).then((resp) => {
            setProjectConfigModalShow(false)
            setReloadProjects(true)
            // TODO show message
        })
    }


}

useEffect(() => {

    if (reloadProjects)
        fetchAllProjects().then((resp) => {
            if (resp.status === 200) {
                setProjects(resp.data);
                setReloadProjects(false)
            } else {
                console.error("fetch project error")
            }

        });
}, [reloadProjects])
// const reactGridReady = (reactGrid: SlickgridReactInstance) =>{
//     this.reactGrid = reactGrid;
// }

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
                                <Button variant="primary" title="Add New Project" onClick={() => showConfigModalHandle(null, true)}><Plus /></Button>
                            </ButtonGroup>
                        </ButtonToolbar>
                    </nav>
                </Col>
            </Row>
            <Row className="d-flex flex-grow-1">
                <Col className="d-flex flex-grow-1"><Card className="flex-grow-1">
                    <Card.Body>
                        <SlickgridReact ref={gridRef} gridId={`${containerId}-grid`}
                            columnDefinitions={columns}
                            gridOptions={gridOptions}
                            dataset={projects}
                        // onClick={$event => handleGridClick($event)}
                        // onReactGridCreated={$event => reactGridReady($event.detail)}
                        />
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
                    <Modal.Title>{isCreateProject ? 'New Project' : 'Edit Project'}

                    </Modal.Title>

                </Modal.Header>

                <Modal.Body>

                    <Form.Text className="text-muted">
                        {isCreateProject ? 'Create a New' : 'Update The'} Project Below
                    </Form.Text>
                    <Form.Group className="mb-3">
                        <Form.Label>Name</Form.Label>
                        <Form.Control name="name" type="text" placeholder="Enter Project Name" defaultValue={selectedProject?selectedProject.name:''}/>
                    </Form.Group>

                    <Form.Group className="mb-3">
                        <Form.Label>Dataset Size</Form.Label>
                        <Form.Select name="is_dataset_large" value={selectedProject?selectedProject.is_dataset_large:false} onChange={(e)=>{
                            setSelectedProject({...selectedProject, is_dataset_large:e.target.value})
                        }}>
                            <option value="false" >{"< 1000 Whole Slide Images"}</option>
                            <option value="true" >{"> 1000 Whole Slide Images"}</option>
                        </Form.Select>
                    </Form.Group>

                    <Form.Group className="mb-3">
                        <Form.Label>Description</Form.Label>
                        <Form.Control name="description" as="textarea" placeholder="Enter Project Description" rows={3} defaultValue={selectedProject?selectedProject.description:''}/>
                    </Form.Group>

                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={handleCloseConfigModal}>
                        Cancel
                    </Button>
                    <Button variant="primary" type="submit">
                        {isCreateProject ? 'Add' : 'Update'}
                    </Button>
                </Modal.Footer>
            </Form>
        </Modal>

    </>
)
}


export default LandingPage