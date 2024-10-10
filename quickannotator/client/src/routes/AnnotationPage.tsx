import { useOutletContext } from 'react-router-dom';

const AnnotationPage = () => {
    const { currentProject, setCurrentProject } = useOutletContext();

    return (
        <>
            <div>This will be the annotation page</div>
            <input 
            type="text" 
            placeholder="Enter your annotation here" 
            onChange={(e) => setCurrentProject({ ...currentProject, name: e.target.value })}
            />
        </>
    )
}

export default AnnotationPage