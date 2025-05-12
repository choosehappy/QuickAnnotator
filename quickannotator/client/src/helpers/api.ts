// Generic response type
type ApiResponse<T> = Promise<T>;
import { Image, Project, Annotation, AnnotationResponse, AnnotationClass, Tile, TileIds, PostAnnsArgs, PostOperationArgs, PutAnnArgs, QueryAnnsByPolygonArgs, SearchTileIdsByPolygonArgs } from "../types.ts";
import { Polygon, Point, Feature } from 'geojson'; 

interface FetchOptions extends RequestInit {
    headers?: HeadersInit;
}
const API_URL = '/api/v1';

// GET request method
export const get = async <T>(url: string, options: FetchOptions = {}): ApiResponse<{ data: T, status: number }> => {
    const response = await fetch(`${API_URL}${url}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    return { data, status: response.status };
};

// POST request method
export const post = async <U, T>(url: string, data: U, options: FetchOptions = {}): ApiResponse<{ data: T, status: number }> => {
    const response = await fetch(`${API_URL}${url}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        body: JSON.stringify(data),
        ...options,
    });
    const responseData = await response.json();
    return { data: responseData, status: response.status };
};

// PUT request method
export const put = async <T, U>(url: string, data: U, options: FetchOptions = {}): ApiResponse<{ data: T, status: number }> => {
    const response = await fetch(`${API_URL}${url}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        body: JSON.stringify(data),
        ...options,
    });
    const responseData = await response.json();
    return { data: responseData, status: response.status };
};

// DELETE request method
export const remove = async <T>(url: string, options: FetchOptions = {}): ApiResponse<{ data: T, status: number }> => {
    const response = await fetch(`${API_URL}${url}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    return { data, status: response.status };
};

// Fetch image by ID
export const fetchImage = async (image_id: number) => {
    const query = new URLSearchParams({ image_id: image_id.toString() });
    return await get<Image>(`/image/?${query}`);
}
// Fetch image by ID
export const fetchImageByProjectId = async (project_id: number) => {
    // const query = new URLSearchParams({ project_id: project_id.toString() });
    return await get<Image>(`/image/project/${project_id}`);
}
export const removeImage = async (image_id: number) => {
    const query = new URLSearchParams({image_id: image_id.toString() });
    return await remove(`/image/?${query}`);
}

// Fetch project by ID
export const fetchProject = async (project_id: number) => {
    const query = new URLSearchParams({ project_id: project_id.toString() });
    return await get<Project>(`/project/?${query}`);
}
// Fetch all projects 
export const fetchAllProjects = async () => {
    return await get<Project[]>(`/project/all`);
}
// create a new project
export const createProject = async (project: Project) => {
    return await post<Project, Project>(`/project/`, project);
}

// update a existing project
export const updateProject = async (project: Project) => {
    return await put<Project, Project>(`/project/`, project);
}

export const removeProject = async (project_id: number) => {
    const query = new URLSearchParams({ project_id: project_id.toString()});
    return await remove(`/project/?${query}`);
}


// Fetch annotations
export const fetchAllAnnotations = async (image_id: number, annotation_class_id: number, is_gt: boolean) => {
    return await get<AnnotationResponse[]>(`/annotation/${image_id}/${annotation_class_id}/search?is_gt=${is_gt}`);
}

export const spatialSearchAnnotations = async (image_id: number, annotation_class_id: number, is_gt: boolean, x1: number, y1: number, x2: number, y2: number) => {
    const query = new URLSearchParams({
        is_gt: is_gt.toString(),
        x1: x1.toString(),
        y1: y1.toString(),
        x2: x2.toString(),
        y2: y2.toString(),
    });
    return await get<AnnotationResponse[]>(`/annotation/${image_id}/${annotation_class_id}/search?${query}`);
}

export const getAnnotationsForTileIds = async (image_id: number, annotation_class_id: number, tile_ids: number[], is_gt: boolean) => {
    const requestBody: TileIds = {
        tile_ids: tile_ids,
        is_gt: is_gt,
    };

    return await post<TileIds, AnnotationResponse[]>(`/annotation/${image_id}/${annotation_class_id}/tileids`, requestBody);
}

// Post annotation
export const postAnnotations = async (image_id: number, annotation_class_id: number, polygons: Polygon[]) => {
    const requestBody: PostAnnsArgs = {
        polygons: polygons.map(polygon => JSON.stringify(polygon)),
    };

    return await post<PostAnnsArgs, AnnotationResponse[]>(`/annotation/${image_id}/${annotation_class_id}`, requestBody);
}


export const putAnnotation = async (image_id: number, annotation_class_id: number, annotation: Annotation) => {
    const requestBody: PutAnnArgs = {
        polygon: annotation.polygon,
        annotation_id: annotation.id,
        is_gt: true,
    };

    return await put<PutAnnArgs, AnnotationResponse>(`/annotation/${image_id}/${annotation_class_id}`, requestBody);
}

export const removeAnnotation = async (image_id: number, annotation_class_id: number, annotation_id: number, is_gt: boolean) => {
    const query = new URLSearchParams({ is_gt: is_gt.toString(), annotation_id: annotation_id.toString() });
    return await remove(`/annotation/${image_id}/${annotation_class_id}?${query}`);
}

// Fetch annotation classes
export const fetchAnnotationClasses = async () => {
    return await get<AnnotationClass[]>('/class/search');
}

// Fetch annotation class by ID
export const fetchAnnotationClassById = async (annotation_class_id: number) => {
    const query = new URLSearchParams({ annotation_class_id: annotation_class_id.toString() });
    return await get<AnnotationClass>(`/class/?${query}`);
}

// Start processing annotation class
export const startProcessingAnnotationClass = async (annotation_class_id: number) => {
    return await post<null, void>(`/class/${annotation_class_id}/startproc`, null);
};

// Search tile IDs by bounding box
export const searchTileIds = async (image_id: number, annotation_class_id: number, x1: number, y1: number, x2: number, y2: number, hasgt=false) => {
    const query = new URLSearchParams({
        hasgt: hasgt.toString(),
        x1: x1.toString(),
        y1: y1.toString(),
        x2: x2.toString(),
        y2: y2.toString(),
    });

    return await get<{ tile_ids: number[] }>(`/tile/${image_id}/${annotation_class_id}/search/bbox?${query}`);
}

export const searchTileIdsWithinPolygon = async (image_id: number, annotation_class_id: number, polygon: Polygon, hasgt=false) => {
    const requestBody: SearchTileIdsByPolygonArgs = {
        polygon: JSON.stringify(polygon),
        hasgt: hasgt
    };
    return await post<SearchTileIdsByPolygonArgs, { tile_ids: number[] }>(`/tile/${image_id}/${annotation_class_id}/search/polygon`, requestBody);
};

// Fetch tile by ID
export const fetchTile = async (image_id: number, annotation_class_id: number, tile_id: number) => {
    const query = new URLSearchParams({ image_id: image_id.toString(), annotation_class_id: annotation_class_id.toString(), tile_id: tile_id.toString() });
    return await get<Tile>(`/tile?${query}`);
}

export const operateOnAnnotation = async (annotation: Annotation, polygon2: Polygon, operation: number) => {
    const { annotation_class_id, ...rest } = annotation;
    const requestBody: PostOperationArgs = {
        ...rest,
        polygon2: JSON.stringify(polygon2),
        operation: operation,
    };

    return await post<PostOperationArgs, AnnotationResponse>(`/annotation/operation`, requestBody);
}

export const getAnnotationsWithinPolygon = async (image_id: number, annotation_class_id: number, is_gt: boolean, polygon: Polygon) => {
    const requestBody: QueryAnnsByPolygonArgs = {
        is_gt: is_gt,
        polygon: JSON.stringify(polygon),
    };

    return await post<QueryAnnsByPolygonArgs, AnnotationResponse[]>(`/annotation/${image_id}/${annotation_class_id}/withinpoly`, requestBody);
}


export const predictTile = async (image_id: number, annotation_class_id: number, tile_id: number) => {
    const query = new URLSearchParams({ tile_id: tile_id.toString() });
    return await post<null, Tile>(`/tile/${image_id}/${annotation_class_id}/predict?${query}`, null);
}

export const fetchTileBoundingBox = async (image_id: number, annotation_class_id: number, tile_id: number) => {
    const query = new URLSearchParams({ tile_id: tile_id.toString() });
    return await get<{ bbox_polygon: Polygon }>(`/tile/${image_id}/${annotation_class_id}/bbox?${query}`);
}