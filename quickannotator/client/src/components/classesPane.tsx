import Card from 'react-bootstrap/Card';


const ClassesPane = ({selectedClass, setSelectedClass}) => {
    return (
        <Card>
            <Card.Header as={'h5'}>Classes</Card.Header>
            <Card.Body>
                The classes list will go here.
            </Card.Body>
        </Card>
    )
}

export default ClassesPane;