import Nav from 'react-bootstrap/Nav';
import { Link, useOutletContext, useParams } from "react-router-dom";
import { useEffect, useState } from 'react';
import { Modal, Container, Row, Col, Card, ButtonToolbar, ButtonGroup, Button, ListGroup } from "react-bootstrap";
import { Fullscreen, CloudArrowUp, GearFill, Download, AspectRatioFill, Brush, Magic, Eraser, Heptagon, CurrencyBitcoin } from 'react-bootstrap-icons';

import { fetchProject, fetchImageByProjectId, removeImage } from "../helpers/api.ts"
import { Image, OutletContextType } from "../types.ts";
import './project.css'
import ImageTable from '../components/imageTable/imageTable.tsx';
import FileDropUploader from '../components/fileDropUploader/fileDropUploader.tsx'
import ExportAnnotationsModal from '../components/exportAnnotationsModal/exportAnnotationsModal.tsx'

const ProjectPage = () => {
    const { projectid } = useParams();
    const { currentProject, setCurrentProject } = useOutletContext<OutletContextType>();

    const [images, setImages] = useState<Image[]>([])

    const [settingShow, setSettingShow] = useState<boolean>(false)
    const [reloadImages, setReloadImages] = useState<boolean>(false)
    const [embeddingShow, setEmbeddingShow] = useState<boolean>(false)
    const [exportAnnotationsShow, setExportAnnotationsShow] = useState<boolean>(false)


    useEffect(() => {
        fetchProject(parseInt(projectid)).then((resp) => {
            setCurrentProject(resp);
        });
        fetchImageByProjectId(parseInt(projectid)).then((resp) => {
            console.log(resp)
            if (resp.status === 200) {
                setImages(resp.data);
            }

        });

    }, [])
    useEffect(() => {

        if (reloadImages)
            fetchImageByProjectId(parseInt(projectid)).then((resp) => {
                console.log(resp)
                if (resp.status === 200) {
                    setImages(resp.data);
                    setReloadImages(false);
                }
            });
    }, [reloadImages])

    const handleExportClose = () => setExportAnnotationsShow(false);
    const handleExportShow = () => setExportAnnotationsShow(true);

    const handleSettingShow = () => {
        if (embeddingShow) setEmbeddingShow(false)
        setSettingShow(!settingShow)
    };

    const handleEnbeddingShow = () => {
        if (settingShow) setSettingShow(false)
        setEmbeddingShow(!embeddingShow)
    };

    const handleExport = () => {
        console.log('export Annotation...')
    }
    const deleteImageHandle = (imageId) => {

        console.log('deleteImageHandle', imageId)
        removeImage(imageId).then((resp) => {
            console.log('remove image', resp)
            setReloadImages(true);
        })
    };

    // const settingClickHandler = () => {
    // }
    // const settingClickHandler = () => {
    // }
    // const { currentProject, setCurrentProject, currentImage, setCurrentImage } = useOutletContext<OutletContextType>();
    // const imageid = 1;
    // const { projectid } = useParams();

    // useEffect(() => {
    //     setCurrentImage(null);
    //     fetchProject(parseInt(projectid)).then((resp) => {
    //         setCurrentProject(resp);
    //     })
    // }, [])
    console.log('projectid', projectid)
    console.log('setCurrentProject', currentProject)
    // if (currentProject) {
    return (
        <>
            <Container fluid className="pb-3 bg-dark d-flex flex-column flex-grow-1">
                <Row className="d-flex">
                    <Col>
                        <nav className="navbar float-end">
                            <ButtonToolbar aria-label="Toolbar with button groups">
                                <ButtonGroup className={"me-2"}>
                                    <Button variant="primary" title="Show Enbedding" className={`${embeddingShow ? 'active' : ''}`}
                                        onClick={handleEnbeddingShow}
                                    ><AspectRatioFill /></Button>
                                    <Button variant="primary" title="Export Annotations" className={`${exportAnnotationsShow ? 'active' : ''}`}
                                        onClick={handleExportShow}
                                    ><Download /></Button>
                                    <Button variant="secondary" title="Setting" className={`${settingShow ? 'active' : ''}`}
                                        onClick={handleSettingShow}
                                    ><GearFill /></Button>
                                </ButtonGroup>
                            </ButtonToolbar>
                        </nav>
                    </Col>
                </Row>
                <Row className="d-flex flex-grow-1">
                    <Col className={"d-flex flex-grow-1"} xs={(!embeddingShow && !settingShow) ? "12" : "6"}>
                        <Card className="flex-grow-1">
                            <Card.Body id='img_table'>
                                <ImageTable containerId='img_table' project={currentProject} images={images} changed={(!embeddingShow && !settingShow)} deleteHandler={deleteImageHandle} />
                            </Card.Body>
                            <Card.Footer className='d-flex justify-content-center'>
                                <FileDropUploader project_id={projectid} reloadHandler={setReloadImages} />
                            </Card.Footer>
                        </Card>
                    </Col>

                    {settingShow && <Col xs={6}>
                        <Card className="d-flex flex-grow-1 h-100">
                            <Card.Header as={'h5'}>Setting</Card.Header>
                            <Card.Body>
                                <textarea style={{ height: '100%', width: '100%' }}>

                                </textarea>
                            </Card.Body>
                        </Card>
                    </Col>}
                    {embeddingShow && <Col xs={6}>
                        <Card className="d-flex flex-grow-1 h-100">
                            <Card.Header as={'h5'}>Enbedding</Card.Header>
                            <Card.Body>
                                embedding view
                            </Card.Body>
                        </Card>
                    </Col>}
                </Row>
            </Container>
            <ExportAnnotationsModal show={exportAnnotationsShow} handleClose={handleExportClose} />
        </>
    )

}

export default ProjectPage