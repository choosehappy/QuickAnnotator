export default interface Image {
    id: number;
    project_id: number;
    name: string;
    path: string;
    height: number;
    width: number;
    dz_tilesize: number;
    embeddingCoord: string;
    group_id: number;
    split: number;
    date: Date;
}

export const initialImage: Image = {
    id: 0,
    project_id: 0,
    name: "Image 1",
    path: "path/to/image",
    height: 100,
    width: 100,
    dz_tilesize: 0,
    embeddingCoord: "0,0",
    group_id: 0,
    split: 0,
    date: new Date()
}