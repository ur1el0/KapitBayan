import type { AxiosResponse } from 'axios';

let serverTimeOffsetMs = 0;
let hasSyncedServerTime = false;

/**
 * Updates the global server-clock skew whenever a valid server timestamp or Date header is observed.
 */
export function updateServerClockSkew(response: AxiosResponse): void {
    const rawHeader = response.headers?.['x-server-time'] || response.headers?.['date'];
    if (!rawHeader) return;

    const parsedServerMs = Date.parse(rawHeader);
    if (!Number.isNaN(parsedServerMs)) {
        serverTimeOffsetMs = parsedServerMs - Date.now();
        hasSyncedServerTime = true;
    }
}

/**
 * Returns a Date object synchronized with the server's authoritative clock.
 * If the client's local device clock was changed, this offset corrects it.
 */
export function getSynchronizedServerDate(): Date {
    return new Date(Date.now() + serverTimeOffsetMs);
}

/**
 * Returns current synchronized server timestamp in milliseconds.
 */
export function getSynchronizedServerNow(): number {
    return Date.now() + serverTimeOffsetMs;
}

/**
 * Resets clock skew (primarily used for unit testing).
 */
export function resetServerClockSkewForTesting(): void {
    serverTimeOffsetMs = 0;
    hasSyncedServerTime = false;
}

export function isServerTimeSynchronized(): boolean {
    return hasSyncedServerTime;
}
