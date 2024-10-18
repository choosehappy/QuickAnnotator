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
