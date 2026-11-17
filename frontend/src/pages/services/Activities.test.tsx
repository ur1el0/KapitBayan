import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { Activities } from './Activities';

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        post: vi.fn(),
        delete: vi.fn(),
    },
}));

vi.mock('react-hot-toast', () => ({
    default: { error: vi.fn(), success: vi.fn() },
}));

const activity = {
    id: 12,
    title: 'Barangay Assembly',
    description: 'Monthly community meeting.',
    location: 'Covered Court',
    event_datetime: '2026-10-20T09:00:00Z',
    created_at: '2026-10-12T08:00:00Z',
};

describe('Activities', () => {
    beforeEach(() => {
        vi.mocked(axiosPrivate.get).mockReset();
        vi.mocked(axiosPrivate.post).mockReset();
        vi.mocked(axiosPrivate.delete).mockReset();
        vi.mocked(axiosPrivate.get).mockResolvedValue({ data: [] } as never);
    });

    it('shows an accessible load error and keeps scheduling available after the list request fails', async () => {
        vi.mocked(axiosPrivate.get).mockRejectedValueOnce(new Error('Network unavailable'));

        render(<Activities />);

        expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't load activities.");
        expect(screen.queryByText('No upcoming activities scheduled.')).not.toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'Schedule Activity' }));
        expect(screen.getByRole('dialog', { name: 'Schedule Activity' })).toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenCalledExactlyOnceWith('/activities/');
        expect(axiosPrivate.post).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('retries the same list endpoint after repeated failure and renders activities on recovery', async () => {
        vi.mocked(axiosPrivate.get)
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockResolvedValueOnce({ data: { results: [activity] } } as never);

        render(<Activities />);
        expect(await screen.findByRole('alert')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
        await waitFor(() => expect(axiosPrivate.get).toHaveBeenCalledTimes(2));
        expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't load activities.");

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(await screen.findByText('Barangay Assembly')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(screen.queryByText('No upcoming activities scheduled.')).not.toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(1, '/activities/');
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(2, '/activities/');
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(3, '/activities/');
        expect(axiosPrivate.post).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('preserves loaded activity cards when the post-create list refresh fails', async () => {
        vi.mocked(axiosPrivate.get)
            .mockResolvedValueOnce({ data: [activity] } as never)
            .mockRejectedValueOnce(new Error('Network unavailable'));
        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({ data: {} } as never);

        render(<Activities />);
        expect(await screen.findByText('Barangay Assembly')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Schedule Activity' }));
        fireEvent.change(screen.getByLabelText('Event Title'), { target: { value: 'Health Screening' } });
        fireEvent.change(screen.getByLabelText('Location'), { target: { value: 'Barangay Hall' } });
        fireEvent.change(screen.getByLabelText('Date & Time'), { target: { value: '2030-10-20T09:00' } });
        fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Community health screening.' } });
        fireEvent.click(screen.getByRole('button', { name: 'Schedule Event' }));

        await waitFor(() => expect(axiosPrivate.get).toHaveBeenCalledTimes(2));

        expect(screen.getByText('Barangay Assembly')).toBeInTheDocument();
        expect(screen.getByRole('alert')).toHaveTextContent("We couldn't load activities.");
        expect(axiosPrivate.post).toHaveBeenCalledWith('/activities/', expect.objectContaining({
            title: 'Health Screening',
            location: 'Barangay Hall',
        }));
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('shows the genuine empty state after a successful empty response', async () => {
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({ data: [] } as never);

        render(<Activities />);

        expect(await screen.findByText('No upcoming activities scheduled.')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('disables retry while the GET is pending without blocking scheduling or invoking mutations', async () => {
        vi.mocked(axiosPrivate.get)
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockImplementationOnce(() => new Promise(() => {}));

        render(<Activities />);
        await screen.findByRole('alert');
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(await screen.findByRole('button', { name: 'Trying again…' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Schedule Activity' })).toBeEnabled();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(2);
        expect(axiosPrivate.post).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('blocks scheduling an activity with a past date or past same-day time', async () => {
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({ data: [] } as never);

        render(<Activities />);
        await screen.findByText('No upcoming activities scheduled.');

        fireEvent.click(screen.getByRole('button', { name: 'Schedule Activity' }));

        const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
        oneHourAgo.setMinutes(oneHourAgo.getMinutes() - oneHourAgo.getTimezoneOffset());
        const pastLocalValue = oneHourAgo.toISOString().slice(0, 16);

        const dateInput = screen.getByLabelText('Date & Time');
        expect(dateInput).toHaveAttribute('min');

        fireEvent.change(screen.getByLabelText('Event Title'), { target: { value: 'Past Assembly' } });
        fireEvent.change(screen.getByLabelText('Location'), { target: { value: 'Barangay Hall' } });
        fireEvent.change(dateInput, { target: { value: pastLocalValue } });
        fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Should be blocked.' } });
        fireEvent.click(screen.getByRole('button', { name: 'Schedule Event' }));

        expect(await screen.findByRole('alert')).toHaveTextContent(
            'Activity date and time cannot be in the past.',
        );
        expect(axiosPrivate.post).not.toHaveBeenCalled();
    });

});
