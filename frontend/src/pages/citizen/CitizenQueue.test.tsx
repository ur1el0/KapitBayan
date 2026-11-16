import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { CitizenQueue } from './CitizenQueue';

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        post: vi.fn(),
    },
    resolveApiBaseUrl: vi.fn(() => 'http://localhost:8000/api/v1'),
}));

class MockWebSocket {
    static instances: MockWebSocket[] = [];
    url: string;
    onopen: (() => void) | null = null;
    onmessage: ((event: { data: string }) => void) | null = null;
    onclose: (() => void) | null = null;
    onerror: (() => void) | null = null;
    close = vi.fn();

    constructor(url: string) {
        this.url = url;
        MockWebSocket.instances.push(this);
    }

    emitQueueUpdate() {
        this.onmessage?.({ data: JSON.stringify({ type: 'queue_update' }) });
    }
}

describe('CitizenQueue', () => {
    beforeEach(() => {
        MockWebSocket.instances = [];
        vi.stubGlobal('WebSocket', MockWebSocket);
        window.WebSocket = MockWebSocket as unknown as typeof WebSocket;
        vi.mocked(axiosPrivate.get).mockReset();
        vi.mocked(axiosPrivate.post).mockReset();
        vi.mocked(axiosPrivate.get).mockImplementation(async (path) => {
            if (path === '/tickets/live-status/') {
                return {
                    data: { current_ticket: null, total_waiting: 0, avg_wait_mins: 0 },
                } as never;
            }
            return { data: { results: [] } } as never;
        });
        vi.mocked(axiosPrivate.post).mockResolvedValue({
            data: { ticket_number: 'T001' },
        } as never);
    });

    afterEach(() => {
        cleanup();
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it('asks residents to request staff review and never submits priority fields', async () => {
        render(<CitizenQueue />);

        fireEvent.click(await screen.findByRole('button', { name: /get queue ticket/i }));
        expect(screen.getByText(/staff verify priority lane eligibility/i)).toBeInTheDocument();
        expect(screen.getByLabelText('Select Service')).toBeInTheDocument();
        expect(screen.queryByRole('checkbox', { name: /priority/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /priority lane/i })).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: /confirm ticket/i }));

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith('/tickets/', {
                service_type: 'General service visit',
            });
        });
    });

    it('shows a queue load error instead of an empty ticket state and retries', async () => {
        vi.mocked(axiosPrivate.get).mockRejectedValueOnce(new Error('Network unavailable'));

        render(<CitizenQueue />);

        expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't load your queue details.");
        expect(screen.queryByText('You do not have an active queue ticket')).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /get a ticket now/i })).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        await waitFor(() => {
            expect(screen.getByText('You do not have an active queue ticket')).toBeInTheDocument();
        });
    });

    it('connects to websocket and refreshes queue details when a queue_update event is received', async () => {
        render(<CitizenQueue />);

        await waitFor(() => {
            expect(MockWebSocket.instances.length).toBeGreaterThan(0);
        });

        // Initial fetch calls: /tickets/live-status/ and /tickets/
        const initialCalls = vi.mocked(axiosPrivate.get).mock.calls.length;
        expect(initialCalls).toBe(2);

        // Emit real-time queue_update event from websocket
        MockWebSocket.instances[0].emitQueueUpdate();

        await waitFor(() => {
            expect(vi.mocked(axiosPrivate.get).mock.calls.length).toBeGreaterThan(initialCalls);
        });

        const socket = MockWebSocket.instances[0];
        cleanup();
        expect(socket.close).toHaveBeenCalled();
    });
});
