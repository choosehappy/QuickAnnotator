import {useLocation} from "react-router-dom";
import {useMemo} from "react";

export function useQuery() {
    const { search } = useLocation();

    return useMemo(() => new URLSearchParams(search), [search]);
}

export async function fetchImage(image_id: number) {
    /*  Fetch an image from the backend */
    const queryString = new URLSearchParams({ "image_id": image_id.toString() });
    try {
        const response = await fetch(`/api/v1/image?${queryString}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Error fetching image: ${response.statusText}`);
        }

        return response.json();
    } catch (error) {
        console.error("Fetch error:", error);
        throw error;
    }
}

export async function fetchProject(project_id: number) {
    /*  Fetch a project from the backend */
    try {
        const response = await fetch(`/api/v1/project/?project_id=${project_id}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Error fetching project: ${response.statusText}`);
        }

        return response.json();
    } catch (error) {
        console.error("Fetch error:", error);
        throw error;
    }
}

export async function fetchAnnotations(image_id: number, annotation_class_id: number, is_gt: boolean) {
    try {
        const response = await fetch(`/api/v1/annotation/${image_id}/${annotation_class_id}/search?is_gt=${is_gt}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Error fetching annotations: ${response.statusText}`);
        }

        return response.json();
    } catch (error) {
        console.error("Fetch error:", error);
        throw error;
    }

}

export async function fetchAnnotationClass(annotation_class_id: number | null = null) {
    try {
        let queryString = ""
        if (annotation_class_id) {
            queryString = `/api/v1/class/?annotation_class_id=${annotation_class_id}`
        } else {
            queryString = `/api/v1/class/search`
        }

        const response = await fetch(queryString, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Error fetching annotation class: ${response.statusText}`);
        }

        return response.json();
    } catch (error) {
        console.error("Fetch error:", error);
        throw error;
    }

}