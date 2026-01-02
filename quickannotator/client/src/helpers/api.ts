// Generic response type
type ApiResponse<T> = Promise<T>;
import { Image, Project, Annotation, AnnotationResponse, AnnotationClass, Tile, GetAnnsForTileIdsArgs, PostAnnsArgs, PostOperationArgs, PutAnnArgs, QueryAnnsByPolygonArgs, SearchTileRefsByPolygonArgs, TileRef, PredictTilesRequest, TileWithBbox} from "../types.ts";
import { Polygon, Point, Feature } from 'geojson'; 
import { API_URI, POLYGON_OPERATIONS } from "./config.ts";

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
export const put = async <U, T>(url: string, data: U, options: FetchOptions = {}): ApiResponse<{ data: T, status: number }> => {
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
export const fetchImagesByProjectId = async (project_id: number) => {
    return await get<Image[]>(`/image/${project_id}/search`);
}
export const removeImage = async (image_id: number) => {
    const query = new URLSearchParams({image_id: image_id.toString() });
    return await remove(`/image/?${query}`);
}

// Fetch image metadata
export const fetchImageMetadata = async (image_id: number) => {
    return await get<{ mpp: number }>(`/image/${image_id}/metadata`);
};

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
export const fetchAllAnnotations = async (image_id: number, annotation_class_id: number, is_gt: boolean, simplify_tolerance = 0.0) => {
    const query = new URLSearchParams({
        is_gt: is_gt.toString(),
        simplify_tolerance: simplify_tolerance.toString(),
    });
    return await get<AnnotationResponse[]>(`/annotation/${image_id}/${annotation_class_id}/search?${query}`);
};

export const spatialSearchAnnotations = async (image_id: number, annotation_class_id: number, is_gt: boolean, x1: number, y1: number, x2: number, y2: number, simplify_tolerance = 0.0) => {
    const query = new URLSearchParams({
        is_gt: is_gt.toString(),
        x1: x1.toString(),
        y1: y1.toString(),
        x2: x2.toString(),
        y2: y2.toString(),
        simplify_tolerance: simplify_tolerance.toString(),
    });
    return await get<AnnotationResponse[]>(`/annotation/${image_id}/${annotation_class_id}/search?${query}`);
};

export const getAnnotationsForTileIds = async (image_id: number, annotation_class_id: number, tile_ids: number[], is_gt: boolean, simplify_tolerance = 0.0) => {
    const requestBody: GetAnnsForTileIdsArgs = {
        tile_ids: tile_ids,
        is_gt: is_gt,
        simplify_tolerance: simplify_tolerance,
    };

    return await post<GetAnnsForTileIdsArgs, AnnotationResponse[]>(`/annotation/${image_id}/${annotation_class_id}/tileids`, requestBody);
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
export const searchAnnotationClasses = async (project_id?: number) => {
    const query = project_id ? new URLSearchParams({ project_id: project_id.toString() }) : new URLSearchParams();
    return await get<AnnotationClass[]>(`/class/search?${query}`);
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

export const createAnnotationClass = async (project_id: number, name: string, color: string, work_mag: number, tile_size: number) => {
    const query = new URLSearchParams({
        project_id: project_id.toString(),
        name: name,
        color: color,
        work_mag: work_mag.toString(),
        tile_size: tile_size.toString(),
    });

    return await post<null, { annotation_class_id: number }>(`/class/?${query}`, null);
};

export const deleteAnnotationClass = async (annotation_class_id: number) => {
    const query = new URLSearchParams({ annotation_class_id: annotation_class_id.toString() });
    return await remove(`/class/?${query}`);
}

// Search tile IDs by bounding box
export const searchTileRefsByBbox = async (image_id: number, annotation_class_id: number, x1: number, y1: number, x2: number, y2: number, hasgt=false, downsample_level=0) => {
    const query = new URLSearchParams({
        hasgt: hasgt.toString(),
        x1: x1.toString(),
        y1: y1.toString(),
        x2: x2.toString(),
        y2: y2.toString(),
        downsample_level: downsample_level.toString(),
    });

    return await get<TileRef[]>(`/tile/${image_id}/${annotation_class_id}/search/bbox?${query}`);
}

export const searchTileRefsWithinPolygon = async (image_id: number, annotation_class_id: number, polygon: Polygon, hasgt=false) => {
    const requestBody: SearchTileRefsByPolygonArgs = {
        polygon: JSON.stringify(polygon),
        hasgt: hasgt
    };
    return await post<SearchTileRefsByPolygonArgs, TileRef[]>(`/tile/${image_id}/${annotation_class_id}/search/polygon`, requestBody);
};

// Fetch tile by ID
export const fetchTile = async (image_id: number, annotation_class_id: number, tile_id: number) => {
    const query = new URLSearchParams({ image_id: image_id.toString(), annotation_class_id: annotation_class_id.toString(), tile_id: tile_id.toString() });
    return await get<Tile>(`/tile?${query}`);
}

export const operateOnAnnotation = async (annotation: Annotation, polygon2: Polygon, operation: POLYGON_OPERATIONS) => {
    const { annotation_class_id, featureId,...rest } = annotation;
    const requestBody: PostOperationArgs = {
        ...rest,
        polygon2: JSON.stringify(polygon2),
        operation: operation,
    };

    return await post<PostOperationArgs, AnnotationResponse>(`/annotation/operation`, requestBody);
}

export const getAnnotationsWithinPolygon = async (image_id: number, annotation_class_id: number, is_gt: boolean, polygon: Polygon, simplify_tolerance = 0.0) => {
    const requestBody: QueryAnnsByPolygonArgs = {
        is_gt: is_gt,
        polygon: JSON.stringify(polygon),
        simplify_tolerance: simplify_tolerance,
    };

    return await post<QueryAnnsByPolygonArgs, AnnotationResponse[]>(`/annotation/${image_id}/${annotation_class_id}/withinpoly`, requestBody);
}


export const predictTiles = async (image_id: number, annotation_class_id: number, tile_ids: number[], include_bbox = false) => {
    const requestBody: PredictTilesRequest = { tile_ids, include_bbox };
    return await post<PredictTilesRequest, Tile[] | TileWithBbox[]>(`/tile/${image_id}/${annotation_class_id}/predict`, requestBody);
}

// Fetch a new color for a project
export const fetchNewColor = async (project_id: number) => {
    return await get<{ color: string }>(`/class/color/${project_id}`);
};

// Fetch available magnifications
export const fetchMagnifications = async () => {
    return await get<{ magnifications: number[] }>('/class/magnifications');
};

// Fetch all available tile sizes
export const fetchTilesizes = async () => {
    return await get<{ tilesizes: number[] }>('/class/tilesizes');
}
export const exportAnnotationsToServer = async (
    image_ids: number[],
    annotation_class_ids: number[],
    export_formats: string[]
) => {
    const query = new URLSearchParams();
    image_ids.forEach(id => query.append('image_ids', id.toString()));
    annotation_class_ids.forEach(id => query.append('annotation_class_ids', id.toString()));
    export_formats.forEach(format => query.append('export_formats', format));

    const response = await post<null, { actor_name: string; filepaths: string[] }>(
        `/annotation/export/server?${query}`,
        null
    );

    if (response.status !== 202) {
        throw new Error(`Failed to export annotations to server`);
    }

    const manifestContent = response.data.filepaths
        .map(filepath => `${window.location.origin}${API_URI}/annotation/export/download/${filepath}`)
        .join('\n');

    const blob = new Blob([manifestContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'manifest.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    return response.data;
};

export const exportAnnotationsToDSA = async (
    image_ids: number[],
    annotation_class_ids: number[],
    api_uri: string,
    api_key: string,
    folder_id: string
) => {
    const requestBody = {
        image_ids: image_ids,
        annotation_class_ids: annotation_class_ids,
        api_uri: api_uri,
        api_key: api_key,
        folder_id: folder_id,
    };

    const response = await post<typeof requestBody, { actor_name: string }>(
        `/annotation/export/dsa`,
        requestBody
    );

    if (response.status !== 202) {
        throw new Error(`Failed to export annotations to DSA`);
    }

    return response.data;
};



export const getAnnotationPageURL = (project_id: number, image_id: number) => `/project/${project_id}/annotate/${image_id}`

export const getImageThumbnailURL = (image_id: number) =>`/api/v1/image/${image_id}/1/file`

export const UploadImageURL = () =>`/api/v1/image/upload`;

// Ray cluster / task helpers
// Fetch a single Ray task by its task id
export const fetchRayTaskById = async (task_id: string) => {
    return await get<any>(`/ray/task/${task_id}`);
};

// List Ray tasks using RayClusterStateFilters. The server expects a JSON body
// with a `ray_cluster_filters` array. Returns an array of task state objects.
export const searchRayTasks = async (ray_cluster_filters: any[] = []) => {
    const requestBody = { ray_cluster_filters };
    return await post<typeof requestBody, any[]>(`/ray/task`, requestBody);
};

export const getChildRayTasks = async (parent_task_id: string) => {
    const filters = [["parent_task_id", "=", parent_task_id], ["type", "=", "ACTOR_TASK"]];
    return await searchRayTasks(filters);
}

export const searchTileByCoordinates = async (image_id: number, annotation_class_id: number, x: number, y: number, downsample_level = 0): ApiResponse<{ data: TileRef }> => {
    const query = new URLSearchParams({
        x: x.toString(),
        y: y.toString(),
        downsample_level: downsample_level.toString(),
    });
    return get<TileRef>(
        `/tile/${image_id}/${annotation_class_id}/search/coordinates?${query}`
    );
};

export const fetchTileBoundingBoxes = async (image_id: number, annotation_class_id: number, tile_ids: number[]) => {
    const requestBody = { tile_ids };
    return await post<{ tile_ids: number[] }, { tile_id: number; bbox_polygon: any }[]>(
        `/tile/${image_id}/${annotation_class_id}/bbox`,
        requestBody
    );
};