import { describe, it, expect, beforeEach } from 'vitest';
import {
    updateServerClockSkew,
    getSynchronizedServerDate,
    getSynchronizedServerNow,
    resetServerClockSkewForTesting,
    isServerTimeSynchronized,
} from './serverTime';
import type { AxiosResponse } from 'axios';

describe('serverTime utility', () => {
    beforeEach(() => {
        resetServerClockSkewForTesting();
    });

    it('defaults to local time when no server header has arrived', () => {
        expect(isServerTimeSynchronized()).toBe(false);
        const diff = Math.abs(getSynchronizedServerNow() - Date.now());
        expect(diff).toBeLessThan(100);
    });

    it('calculates clock skew from X-Server-Time header', () => {
        const futureServerTime = new Date(Date.now() + 3_600_000).toISOString(); // 1 hour ahead
        const fakeResponse = {
            headers: {
                'x-server-time': futureServerTime,
            },
        } as unknown as AxiosResponse;

        updateServerClockSkew(fakeResponse);

        expect(isServerTimeSynchronized()).toBe(true);
        const offset = getSynchronizedServerNow() - Date.now();
        expect(offset).toBeGreaterThan(3_500_000);
        expect(offset).toBeLessThanOrEqual(3_600_000);

        const syncDate = getSynchronizedServerDate();
        expect(syncDate.getTime()).toBeGreaterThan(Date.now() + 3_500_000);
    });

    it('falls back to standard Date header if X-Server-Time is missing', () => {
        const pastServerTime = new Date(Date.now() - 7_200_000).toUTCString(); // 2 hours behind
        const fakeResponse = {
            headers: {
                date: pastServerTime,
            },
        } as unknown as AxiosResponse;

        updateServerClockSkew(fakeResponse);

        expect(isServerTimeSynchronized()).toBe(true);
        const offset = getSynchronizedServerNow() - Date.now();
        expect(offset).toBeLessThan(-7_000_000);
    });
});
