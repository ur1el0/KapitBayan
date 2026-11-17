import axios from 'axios';
import { updateServerClockSkew } from '../utils/serverTime';
import {
    clearAccessToken,
    getAccessToken,
    getAccessTokenVersion,
    hasExplicitLogout,
    setAccessToken,
} from './accessToken';

// Base URL resolution helper supporting build-time env injection and fallback
export function resolveApiBaseUrl(
    envUrl = import.meta.env.VITE_API_BASE_URL,
    isProd = import.meta.env.PROD
): string {
    if (isProd) {
        return '/api/v1';
    }
    if (envUrl) {
        return envUrl;
    }
    return 'http://localhost:8000/api/v1';
}

const BASE_URL = resolveApiBaseUrl();
const REQUEST_TIMEOUT_MS = 35_000;

export const axiosPrivate = axios.create({
    baseURL: BASE_URL,
    timeout: REQUEST_TIMEOUT_MS,
    headers: { 'Content-Type': 'application/json' },
    withCredentials: true, // IMPORTANT: Allows sending HttpOnly cookies for JWT
});

export const axiosPublic = axios.create({
    baseURL: BASE_URL,
    timeout: REQUEST_TIMEOUT_MS,
    headers: { 'Content-Type': 'application/json' },
    withCredentials: true,
});

axiosPublic.interceptors.response.use(
    (response) => {
        updateServerClockSkew(response);
        return response;
    },
    (error) => {
        if (error?.response) {
            updateServerClockSkew(error.response);
        }
        return Promise.reject(error);
    }
);

let refreshRequest: Promise<string> | null = null;

function refreshAccessToken(): Promise<string> {
    if (hasExplicitLogout()) {
        return Promise.reject(new Error('Session was explicitly logged out.'));
    }

    if (!refreshRequest) {
        refreshRequest = axios.post(`${BASE_URL}/auth/token/refresh/`, {}, {
            withCredentials: true,
            timeout: REQUEST_TIMEOUT_MS,
        }).then((response) => {
            const access = response.data?.access;
            if (typeof access !== 'string' || access.length === 0) {
                throw new Error('The session refresh response did not include an access token.');
            }
            if (hasExplicitLogout()) {
                throw new Error('Session was explicitly logged out.');
            }
            setAccessToken(access);
            return access;
        }).finally(() => {
            refreshRequest = null;
        });
    }

    return refreshRequest;
}

// Request interceptor to append the access token
axiosPrivate.interceptors.request.use(
    (config) => {
        const token = getAccessToken();
        (config as typeof config & { _authVersion?: number })._authVersion = getAccessTokenVersion();
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor to handle 401s and refresh the token
axiosPrivate.interceptors.response.use(
    (response) => {
        updateServerClockSkew(response);
        return response;
    },
    async (error) => {
        if (error.response) {
            updateServerClockSkew(error.response);
        }
        const originalRequest = error.config as (typeof error.config & {
            _retry?: boolean;
            _authVersion?: number;
        }) | undefined;

        if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                let access = getAccessToken();
                if (!access || originalRequest._authVersion === getAccessTokenVersion()) {
                    access = await refreshAccessToken();
                }

                // Retry the original request with the new token
                if (originalRequest.headers) {
                    originalRequest.headers.Authorization = `Bearer ${access}`;
                }
                return axiosPrivate(originalRequest);
            } catch (refreshError) {
                // Only expire the session if another login/logout has not replaced this request.
                if (originalRequest._authVersion === getAccessTokenVersion()) {
                    clearAccessToken();
                    window.dispatchEvent(new Event('gridy:session-expired'));
                }
                return Promise.reject(refreshError);
            }
        }
        return Promise.reject(error);
    }
);
