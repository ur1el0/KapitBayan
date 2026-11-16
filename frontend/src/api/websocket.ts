import { resolveApiBaseUrl } from './axios';

/**
 * Resolves the WebSocket URL for real-time queue notifications.
 * Connects to ws:// or wss:// based on the current origin and environment.
 * If barangayId is provided, scopes the route to /ws/queue/{barangayId}/.
 */
export function resolveQueueWsUrl(barangayId?: string | number | null): string {
    const customWs = import.meta.env.VITE_WS_BASE_URL;
    if (customWs) {
        const base = customWs.replace(/\/+$/, '');
        return barangayId ? `${base}/ws/queue/${barangayId}/` : `${base}/ws/queue/`;
    }

    const apiUrl = resolveApiBaseUrl();
    if (apiUrl.startsWith('http://') || apiUrl.startsWith('https://')) {
        const parsed = new URL(apiUrl);
        const wsProto = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
        const path = barangayId ? `/ws/queue/${barangayId}/` : `/ws/queue/`;
        return `${wsProto}//${parsed.host}${path}`;
    }

    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const path = barangayId ? `/ws/queue/${barangayId}/` : `/ws/queue/`;
    return `${wsProto}//${window.location.host}${path}`;
}
