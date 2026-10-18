import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { axiosPrivate } from '../../api/axios';
import { AuthContext, type AuthContextType } from '../../context/auth-context';
import { Dashboard } from './Dashboard';

vi.mock('../../api/axios', () => ({
    axiosPrivate: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const summary = {
    total_residents: 37,
    document_requests: {
        total: 10,
        pending: 4,
        approved: 2,
        rejected: 1,
        released: 3,
        total_revenue: 1250,
    },
    issue_reports: {
        total: 8,
        pending: 2,
        in_progress: 3,
        resolved: 3,
        urgency_breakdown: { low: 1, medium: 2, high: 3, urgent: 2 },
        scenario_breakdown: {
            peace_and_order: 1,
            public_health: 2,
            infrastructure: 3,
            environment: 1,
            other: 1,
        },
        time_of_day: { night_time: 4, day_time: 4 },
    },
    queue_activity: { total_today: 5, serving_now: null, waiting_count: 2 },
    demographics: {
        purok_distribution: { 'Purok 1': 20, 'Purok 2': 17 },
        age_demographics: { youth: 8, young_adult: 10, adult: 12, senior: 7 },
    },
};

const activities = [{
    id: 8,
    title: 'Community Health Day',
    description: 'Barangay health screening',
    location: 'Barangay Hall',
    event_datetime: '2030-01-15T09:00:00Z',
    created_at: '2029-12-01T00:00:00Z',
}];

const makeAuthContext = (role: string): AuthContextType => ({
    user: { role, barangay: { name: 'Cotta' } },
    login: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    isAuthenticated: true,
    updateBarangayPrimaryColor: vi.fn(),
});

const renderDashboard = (role = 'ADMIN') => render(
    <AuthContext.Provider value={makeAuthContext(role)}>
        <MemoryRouter initialEntries={['/admin']}>
            <Routes>
                <Route path="/admin" element={<Dashboard />} />
            </Routes>
        </MemoryRouter>
    </AuthContext.Provider>,
);

describe('Dashboard', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(axiosPrivate.get)
            .mockResolvedValueOnce({ data: summary } as never)
            .mockResolvedValueOnce({ data: { results: activities } } as never);
    });

    it('renders barangay metrics and scheduled activities from the API', async () => {
        renderDashboard();

        expect(await screen.findByText('Community Health Day')).toBeInTheDocument();
        expect(screen.getByText('Administrative Overview')).toBeInTheDocument();
        expect(screen.getByText('Total Registered Residents')).toBeInTheDocument();
        expect(screen.getByText('37', { exact: true })).toBeInTheDocument();
        expect(screen.getByText('4', { exact: true })).toBeInTheDocument();
        expect(screen.getByText('₱1,250.00')).toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(1, '/dashboard/summary/', expect.anything());
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(2, '/activities/', expect.anything());
    });

    it('treats an HTML summary response as a failed read without crashing the dashboard', async () => {
        vi.mocked(axiosPrivate.get).mockReset();
        vi.mocked(axiosPrivate.get)
            .mockResolvedValueOnce({ data: '<!doctype html><html><body>KapitBayan</body></html>' } as never)
            .mockResolvedValueOnce({ data: { results: activities } } as never);

        renderDashboard();

        expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't load dashboard summary.");
        expect(screen.getByText('Community Health Day')).toBeInTheDocument();
        expect(screen.queryByText('This screen couldn’t load')).not.toBeInTheDocument();
    });

    it('treats an HTML activities response as a failed read and preserves summary metrics', async () => {
        vi.mocked(axiosPrivate.get).mockReset();
        vi.mocked(axiosPrivate.get)
            .mockResolvedValueOnce({ data: summary } as never)
            .mockResolvedValueOnce({ data: '<!doctype html><html><body>KapitBayan</body></html>' } as never);

        renderDashboard();

        expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't load today's appointments.");
        expect(screen.getByText('₱1,250.00')).toBeInTheDocument();
        expect(screen.queryByText('This screen couldn’t load')).not.toBeInTheDocument();
    });

    it('recovers a failed summary independently while retaining appointments', async () => {
        let summaryReads = 0;
        let activitiesReads = 0;
        let rejectSummaryRetry: (reason: unknown) => void = () => {};
        vi.mocked(axiosPrivate.get).mockReset();
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url === '/dashboard/summary/') {
                summaryReads += 1;
                if (summaryReads === 1) return Promise.reject(new Error('Network unavailable')) as never;
                if (summaryReads === 2) {
                    return new Promise((_resolve, reject) => { rejectSummaryRetry = reject; }) as never;
                }
                return Promise.resolve({ data: summary }) as never;
            }
            activitiesReads += 1;
            return Promise.resolve({ data: { results: activities } }) as never;
        });
        renderDashboard();

        const summaryError = await screen.findByRole('alert');
        expect(summaryError).toHaveTextContent("We couldn't load dashboard summary.");
        expect(screen.getByText('Community Health Day')).toBeInTheDocument();
        expect(screen.queryByText('₱0.00')).not.toBeInTheDocument();

        fireEvent.click(within(summaryError).getByRole('button', { name: 'Try again' }));
        const pendingRetry = await screen.findByRole('button', { name: 'Trying again…' });
        expect(pendingRetry).toBeDisabled();
        rejectSummaryRetry(new Error('Still unavailable'));
        await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent("We couldn't load dashboard summary."));

        fireEvent.click(within(screen.getByRole('alert')).getByRole('button', { name: 'Try again' }));
        expect(await screen.findByText('₱1,250.00')).toBeInTheDocument();
        expect(screen.getByText('Community Health Day')).toBeInTheDocument();
        expect(summaryReads).toBe(3);
        expect(activitiesReads).toBe(1);
        expect(axiosPrivate.post).not.toHaveBeenCalled();
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('recovers a failed appointments read independently while retaining summary metrics', async () => {
        let summaryReads = 0;
        let activitiesReads = 0;
        let rejectActivitiesRetry: (reason: unknown) => void = () => {};
        let resolveActivitiesRetry: (value: unknown) => void = () => {};
        vi.mocked(axiosPrivate.get).mockReset();
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url === '/dashboard/summary/') {
                summaryReads += 1;
                return Promise.resolve({ data: summary }) as never;
            }
            activitiesReads += 1;
            if (activitiesReads === 1) return Promise.reject(new Error('Network unavailable')) as never;
            if (activitiesReads === 2) {
                return new Promise((_resolve, reject) => { rejectActivitiesRetry = reject; }) as never;
            }
            return new Promise((resolve) => { resolveActivitiesRetry = resolve; }) as never;
        });
        renderDashboard();

        const activitiesError = await screen.findByRole('alert');
        expect(activitiesError).toHaveTextContent("We couldn't load today's appointments.");
        expect(screen.queryByText('No appointments or activities scheduled.')).not.toBeInTheDocument();
        expect(screen.getByText('₱1,250.00')).toBeInTheDocument();

        fireEvent.click(within(activitiesError).getByRole('button', { name: 'Try again' }));
        const pendingRetry = await screen.findByRole('button', { name: 'Trying again…' });
        expect(pendingRetry).toBeDisabled();

        rejectActivitiesRetry(new Error('Still unavailable'));
        const repeatedFailureRetry = await screen.findByRole('button', { name: 'Try again' });
        expect(screen.getByRole('alert')).toHaveTextContent("We couldn't load today's appointments.");
        fireEvent.click(repeatedFailureRetry);
        await screen.findByRole('button', { name: 'Trying again…' });
        resolveActivitiesRetry({ data: { results: activities } });

        expect(await screen.findByText('Community Health Day')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(summaryReads).toBe(1);
        expect(activitiesReads).toBe(3);
        expect(axiosPrivate.post).not.toHaveBeenCalled();
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });
});
