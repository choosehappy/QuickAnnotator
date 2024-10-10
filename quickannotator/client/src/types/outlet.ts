import Project from "./project.ts";
import Image from "./image.ts";

export type OutletContextType = {
    currentProject: Project;
    setCurrentProject: (project: Project | null) => void;
    currentImage: Image;
    setCurrentImage: (image: Image | null) => void;
}