import { describe, expect, it, vi, afterEach } from 'vitest';
import { resolveQueueWsUrl } from './websocket';

describe('resolveQueueWsUrl', () => {
    afterEach(() => {
        vi.unstubAllEnvs();
    });

    it('returns barangay-scoped websocket route with ws/wss', () => {
        const url = resolveQueueWsUrl(15);
        expect(url).toContain('/ws/queue/15/');
        expect(url.startsWith('ws://') || url.startsWith('wss://')).toBe(true);
    });

    it('returns generic websocket route when no barangayId is given', () => {
        const url = resolveQueueWsUrl();
        expect(url).toContain('/ws/queue/');
        expect(url.endsWith('/ws/queue/')).toBe(true);
    });

    it('respects VITE_WS_BASE_URL if set in environment', () => {
        vi.stubEnv('VITE_WS_BASE_URL', 'wss://custom.domain.com');
        const url = resolveQueueWsUrl(99);
        expect(url).toBe('wss://custom.domain.com/ws/queue/99/');
    });

    it('strips trailing slashes from VITE_WS_BASE_URL', () => {
        vi.stubEnv('VITE_WS_BASE_URL', 'wss://custom.domain.com///');
        const url = resolveQueueWsUrl(99);
        expect(url).toBe('wss://custom.domain.com/ws/queue/99/');
    });
});
