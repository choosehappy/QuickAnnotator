// Generic response type
type ApiResponse<T> = Promise<T>;
import { Image, Project, Annotation, AnnotationClass, Tile, PostAnnArgs, PostOperationArgs, PutAnnArgs } from "../types.ts";
import { Polygon, Point, Feature } from 'geojson'; 

interface FetchOptions extends RequestInit {
    headers?: HeadersInit;
}
const API_URL = '/api/v1';

// GET request method
export const get = async <T>(url: string, options: FetchOptions = {}): ApiResponse<T> => {
    const response = await fetch(`${API_URL}${url}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });
    if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
    }
    const text = await response.text();
    return text ? JSON.parse(text) : {};
};

// POST request method
export const post = async <U, T>(url: string, data: U, options: FetchOptions = {}): ApiResponse<T> => {
    const response = await fetch(`${API_URL}${url}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        body: JSON.stringify(data),
        ...options,
    });
    if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
    }
    return response.json();
};

// PUT request method
export const put = async <T, U>(url: string, data: U, options: FetchOptions = {}): ApiResponse<T> => {
    const response = await fetch(`${API_URL}${url}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        body: JSON.stringify(data),
        ...options,
    });
    if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
    }
    return response.json();
};

// DELETE request method
export const remove = async <T>(url: string, options: FetchOptions = {}): ApiResponse<T> => {
    const response = await fetch(`${API_URL}${url}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });
    if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
    }

    const text = await response.text();
    return text ? JSON.parse(text) : {};
};

// Fetch image by ID
export const fetchImage = async (image_id: number) => {
    const query = new URLSearchParams({ image_id: image_id.toString() });
    return await get<Image>(`/image/?${query}`);
}

// Fetch project by ID
export const fetchProject = async (project_id: number) => {
    const query = new URLSearchParams({ project_id: project_id.toString() });
    return await get<Project>(`/project/?${query}`);
}

// Fetch annotations
export const fetchAllAnnotations = async (image_id: number, annotation_class_id: number, is_gt: boolean) => {
    return await get<Annotation[]>(`/annotation/${image_id}/${annotation_class_id}/search?is_gt=${is_gt}`);
}

export const searchAnnotations = async (image_id: number, annotation_class_id: number, is_gt: boolean, x1: number, y1: number, x2: number, y2: number) => {
    const query = new URLSearchParams({
        is_gt: is_gt.toString(),
        x1: x1.toString(),
        y1: y1.toString(),
        x2: x2.toString(),
        y2: y2.toString(),
    });
    return await get<Annotation[]>(`/annotation/${image_id}/${annotation_class_id}/search?${query}`);
}

export const searchAnnotationsWithinTile = async (tile: Tile, is_gt: boolean) => {
    const geom = JSON.parse(tile.geom.toString());

    const x1 = Math.round(geom.coordinates[0][0][0]);
    const y1 = Math.round(geom.coordinates[0][0][1]);
    const x2 = Math.round(geom.coordinates[0][2][0]);
    const y2 = Math.round(geom.coordinates[0][2][1]);

    const resp = await searchAnnotations(tile.image_id, tile.annotation_class_id, is_gt, x1, y1, x2, y2)
    return resp
}

// Post annotation
export const postAnnotation = async (image_id: number, annotation_class_id: number, is_gt: boolean, polygon: Polygon) => {
    const requestBody: PostAnnArgs = {
        is_gt: is_gt,
        polygon: JSON.stringify(polygon),
    };

    return await post<PostAnnArgs, Annotation>(`/annotation/${image_id}/${annotation_class_id}`, requestBody);
}

export const putAnnotation = async (image_id: number, annotation_class_id: number, annotation: Annotation) => {
    const requestBody: PutAnnArgs = {
        ...annotation,
        is_gt: true,
    }
    return await put<PutAnnArgs, Annotation>(`/annotation/${image_id}/${annotation_class_id}`, requestBody);;
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

// Fetch annotation by ID
export const searchTiles = async (image_id: number, annotation_class_id: number, x1: number, y1: number, x2: number, y2: number) => {
    const query = new URLSearchParams({
        image_id: image_id.toString(),
        annotation_class_id: annotation_class_id.toString(),
        x1: x1.toString(),
        y1: y1.toString(),
        x2: x2.toString(),
        y2: y2.toString(),
    });
    return await get<Tile[]>(`/tile/search?${query}`);
}

// Fetch tile by ID
export const fetchTile = async (tile_id: number) => {
    const query = new URLSearchParams({ tile_id: tile_id.toString() });
    return await get<Tile>(`/tile?${query}`);
}


export const operateOnAnnotation = async (annotation: Annotation, polygon2: Polygon, operation: number) => {
    const requestBody: PostOperationArgs = {
        ...annotation,
        polygon2: JSON.stringify(polygon2),
        operation: operation,
    };

    return await post<PostOperationArgs, Annotation>(`/annotation/operation`, requestBody);
}