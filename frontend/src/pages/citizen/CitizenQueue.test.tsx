import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { CitizenQueue } from './CitizenQueue';

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        post: vi.fn(),
    },
}));

describe('CitizenQueue', () => {
    beforeEach(() => {
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

    afterEach(() => cleanup());

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
});
