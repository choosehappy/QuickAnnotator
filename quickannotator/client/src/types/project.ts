export default interface Project {
    id: number;
    name: string;
    description: string;
    date: Date;
}

export const initialProject: Project = {
    id: 0,
    name: "Project 1",
    description: "This is the first project",
    date: new Date(),
}