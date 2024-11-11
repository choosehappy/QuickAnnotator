// Generic response type
type ApiResponse<T> = Promise<T>;
import { Image, Project, Annotation, AnnotationClass, Tile } from "../types.ts";

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
    return response.json();
};

// POST request method
export const post = async <T, U>(url: string, data: U, options: FetchOptions = {}): ApiResponse<T> => {
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
    return response.json();
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

// Post annotation
export const postAnnotation = async (data: Annotation) => {
    return await post<Annotation, Annotation>('/annotation/', data);
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