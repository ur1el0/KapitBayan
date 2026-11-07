import axios from 'axios';

function firstErrorMessage(value: unknown): string | undefined {
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) {
        for (const item of value) {
            const message = firstErrorMessage(item);
            if (message) return message;
        }
        return undefined;
    }
    if (value && typeof value === 'object') {
        const entries = Object.entries(value as Record<string, unknown>);
        for (const key of ['detail', 'message', 'error']) {
            const message = firstErrorMessage((value as Record<string, unknown>)[key]);
            if (message) return message;
        }
        for (const [key, nested] of entries) {
            if (key === 'detail' || key === 'message' || key === 'error') continue;
            const message = firstErrorMessage(nested);
            if (message) return message;
        }
    }
    return undefined;
}

export function getSafeApiErrorMessage(error: unknown, fallback: string): string {
    if (!axios.isAxiosError(error)) return fallback;

    const response = error.response;
    if (!response || response.status >= 500) return fallback;

    const message = firstErrorMessage(response.data);

    return message?.trim().slice(0, 300) || fallback;
}
