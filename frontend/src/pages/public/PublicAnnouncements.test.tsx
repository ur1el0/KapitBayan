import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { axiosPublic } from '../../api/axios';
import { PublicAnnouncements } from './PublicAnnouncements';

vi.mock('../../api/axios', () => ({
    axiosPublic: { get: vi.fn() },
}));

const originalScrollIntoViewDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView');

afterEach(() => {
    if (originalScrollIntoViewDescriptor) {
        Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', originalScrollIntoViewDescriptor);
    } else {
        Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView');
    }
});

function renderPublicAnnouncements(initialEntry = '/public/announcements/12') {
    return render(
        <MemoryRouter initialEntries={[initialEntry]}>
            <Routes>
                <Route path="/public/announcements/:barangayId" element={<PublicAnnouncements />} />
            </Routes>
        </MemoryRouter>,
    );
}

describe('PublicAnnouncements', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(axiosPublic.get).mockReset();
    });

    it('shows the public context while the initial request is loading', async () => {
        let resolveLoad!: (response: { data: never[] }) => void;
        const pendingLoad = new Promise<{ data: never[] }>((resolve) => { resolveLoad = resolve; });
        vi.mocked(axiosPublic.get).mockReturnValueOnce(pendingLoad as never);

        renderPublicAnnouncements();

        expect(screen.getByRole('status')).toHaveTextContent('Loading announcements…');
        expect(screen.getByRole('heading', { name: 'Barangay announcements' })).toBeInTheDocument();
        expect(screen.getByText(/Official information is shared here/)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Sign in to KapitBayan' })).toBeInTheDocument();
        expect(screen.queryByText('There are no public announcements at this time.')).not.toBeInTheDocument();

        await act(async () => {
            resolveLoad({ data: [] });
            await pendingLoad;
        });

        expect(screen.getByText('There are no public announcements at this time.')).toBeInTheDocument();
    });

    it('retries only the barangay announcement GET and recovers after a repeated failure', async () => {
        let rejectRetry!: (reason?: unknown) => void;
        const pendingRetry = new Promise<never>((_resolve, reject) => { rejectRetry = reject; });
        vi.mocked(axiosPublic.get)
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockReturnValueOnce(pendingRetry as never)
            .mockResolvedValueOnce({ data: [] } as never);

        renderPublicAnnouncements();

        expect(await screen.findByRole('alert')).toHaveTextContent('Announcements are temporarily unavailable.');
        expect(screen.getByRole('heading', { name: 'Barangay announcements' })).toBeInTheDocument();
        expect(screen.getByText(/Official information is shared here/)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Sign in to KapitBayan' })).toHaveAttribute('href', '/login');
        expect(screen.queryByText('There are no public announcements at this time.')).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(screen.getByRole('button', { name: 'Trying again…' })).toBeDisabled();
        expect(screen.getByRole('heading', { name: 'Barangay announcements' })).toBeInTheDocument();
        expect(screen.getByText(/Official information is shared here/)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Sign in to KapitBayan' })).toBeInTheDocument();
        expect(axiosPublic.get).toHaveBeenNthCalledWith(1, '/public/barangays/12/announcements/');
        expect(axiosPublic.get).toHaveBeenNthCalledWith(2, '/public/barangays/12/announcements/');

        await act(async () => {
            rejectRetry(new Error('Still unavailable'));
            await pendingRetry.catch(() => undefined);
        });

        expect(await screen.findByRole('button', { name: 'Try again' })).toBeEnabled();
        expect(screen.getByRole('alert')).toHaveTextContent('Announcements are temporarily unavailable.');
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(await screen.findByText('There are no public announcements at this time.')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(axiosPublic.get).toHaveBeenCalledTimes(3);
    });

    it('clears the retry error when populated announcements are returned', async () => {
        vi.mocked(axiosPublic.get)
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockResolvedValueOnce({
                data: [{
                    id: 8,
                    title: 'Barangay hall schedule',
                    content: 'The office opens at 8 AM on Monday.',
                    created_at: '2025-01-01T00:00:00Z',
                }],
            } as never);

        renderPublicAnnouncements();

        expect(await screen.findByRole('alert')).toHaveTextContent('Announcements are temporarily unavailable.');
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(await screen.findByRole('heading', { name: 'Barangay hall schedule' })).toBeInTheDocument();
        expect(screen.getByText('The office opens at 8 AM on Monday.')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(axiosPublic.get).toHaveBeenCalledTimes(2);
    });

    it('shows public post details and directs transactions back to KapitBayan', async () => {
        vi.mocked(axiosPublic.get).mockResolvedValue({
            data: [{
                id: 3,
                title: 'Barangay hall schedule',
                content: 'The office opens at 8 AM on Monday.',
                is_pinned: true,
                created_at: '2026-10-08T00:00:00Z',
            }],
        } as never);

        renderPublicAnnouncements();

        expect(await screen.findByRole('heading', { name: 'Barangay hall schedule' })).toBeInTheDocument();
        expect(screen.getByText('The office opens at 8 AM on Monday.')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Sign in to KapitBayan' })).toHaveAttribute('href', '/login');
        expect(axiosPublic.get).toHaveBeenCalledWith('/public/barangays/12/announcements/');
    });

    it('focuses and scrolls to the announcement named by the share link', async () => {
        const scrollIntoView = vi.fn();
        Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
            configurable: true,
            value: scrollIntoView,
        });
        vi.mocked(axiosPublic.get).mockResolvedValue({
            data: [{
                id: 8,
                title: 'Water service interruption',
                content: 'Water service will return at 1 PM.',
                is_pinned: false,
                created_at: '2026-10-12T08:00:00Z',
            }],
        } as never);

        renderPublicAnnouncements('/public/announcements/12#announcement-8');

        const article = await screen.findByRole('article', { name: 'Water service interruption' });
        expect(article).toHaveAttribute('id', 'announcement-8');
        await waitFor(() => expect(article).toHaveFocus());
        expect(scrollIntoView).toHaveBeenCalledWith({ block: 'start' });
    });

    it('explains when a deep-linked announcement is no longer public', async () => {
        vi.mocked(axiosPublic.get).mockResolvedValue({
            data: [{
                id: 8,
                title: 'Another announcement',
                content: 'This is a different public notice.',
                is_pinned: false,
                created_at: '2026-10-12T08:00:00Z',
            }],
        } as never);

        renderPublicAnnouncements('/public/announcements/12#announcement-99');

        expect(await screen.findByText(
            'This announcement is no longer available in the public bulletin.',
        )).toHaveAttribute('role', 'status');
    });
});
