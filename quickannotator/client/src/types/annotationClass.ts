export default interface AnnotationClass {
    id: number;
    project_id: number;
    name: string;
    color: string;
    magnification: number;
    patchsize: number;
    tilesize: number;
    date: Date;
    dl_model_objectref: string;
}