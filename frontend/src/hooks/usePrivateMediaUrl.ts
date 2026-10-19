import { useEffect, useState } from "react";
import { axiosPrivate } from "../api/axios";

interface PrivateMediaState {
    url: string | null;
    isLoading: boolean;
    hasError: boolean;
}

interface PrivateMediaRequestState extends PrivateMediaState {
    path?: string | null;
}

function toApiRelativePath(path: string): string {
    const baseURL = axiosPrivate.defaults?.baseURL;
    if (!baseURL || !path.startsWith("/")) {
        return path;
    }

    let basePath: string;
    try {
        basePath = new URL(baseURL, "http://gridy.local").pathname.replace(/\/+$/, "");
    } catch {
        return path;
    }

    if (!basePath || basePath === "/" || !path.startsWith(`${basePath}/`)) {
        return path;
    }

    return path.slice(basePath.length + 1);
}

export function usePrivateMediaUrl(path?: string | null): PrivateMediaState {
    const [state, setState] = useState<PrivateMediaRequestState>({
        path,
        url: null,
        isLoading: Boolean(path),
        hasError: false,
    });

    useEffect(() => {
        if (!path) {
            setState({ path, url: null, isLoading: false, hasError: false });
            return;
        }

        const controller = new AbortController();
        let objectUrl: string | null = null;
        setState({ path, url: null, isLoading: true, hasError: false });

        axiosPrivate.get<Blob>(toApiRelativePath(path), {
            responseType: "blob",
            signal: controller.signal,
        }).then(({ data }) => {
            if (controller.signal.aborted) {
                return;
            }

            objectUrl = URL.createObjectURL(data);
            setState({ path, url: objectUrl, isLoading: false, hasError: false });
        }).catch(() => {
            if (!controller.signal.aborted) {
                setState({ path, url: null, isLoading: false, hasError: true });
            }
        });

        return () => {
            controller.abort();
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
            }
        };
    }, [path]);

    if (state.path !== path) {
        return { url: null, isLoading: Boolean(path), hasError: false };
    }

    return state;
}
