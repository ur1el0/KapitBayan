import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import toast from 'react-hot-toast';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { Settings } from './Settings';

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
    },
}));

vi.mock('react-hot-toast', () => ({
    default: { error: vi.fn(), success: vi.fn() },
}));

vi.mock('../../components/modals/ChangePasswordModal', () => ({
    ChangePasswordModal: () => null,
}));

const profilePreferences = {
    email_alerts: true,
    push_alerts: false,
};

const activeSession = {
    id: 41,
    ip_address: '192.0.2.10',
    user_agent: 'Chrome Desktop',
    created_at: '2026-10-01T12:00:00Z',
    expires_at: '2026-10-08T12:00:00Z',
    is_revoked: false,
};

const loginEvent = {
    id: 81,
    username: 'field_official_one',
    role: 'FIELD_OFFICIAL',
    ip_address: '192.0.2.11',
    user_agent: 'Chrome Android',
    created_at: '2026-10-02T12:00:00Z',
};

const successfulResponseFor = (url: string, preferences = profilePreferences) => {
    if (url === '/auth/me/') return { data: preferences };
    if (url === '/auth/sessions/') return { data: { results: [activeSession] } };
    return { data: { results: [loginEvent] } };
};

const mockSuccessfulLoads = () => {
    vi.mocked(axiosPrivate.get).mockImplementation((url: string) => Promise.resolve(
        successfulResponseFor(url),
    ) as never);
};

const getPushToggle = () => {
    const label = screen.getByText('Push Notifications (Queue Alerts)');
    const toggle = label.closest('div.flex.items-center.justify-between')?.querySelector('button');
    if (!toggle) throw new Error('Push notification toggle was not rendered');
    return toggle;
};

describe('Settings load recovery', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockSuccessfulLoads();
    });

    it('shows sign-in time, network address, device, and the location limitation', async () => {
        render(<Settings />);

        expect(await screen.findByText('field_official_one')).toBeInTheDocument();
        expect(screen.getByText('IP: 192.0.2.11')).toBeInTheDocument();
        expect(screen.getByText('Chrome Android')).toBeInTheDocument();
        expect(screen.getByText(/IP addresses are approximate network information, not GPS location/)).toBeInTheDocument();
    });

    it('does not expose default notification preferences after their GET fails', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => Promise.resolve(
            url === '/auth/me/'
                ? Promise.reject(new Error('Network unavailable'))
                : successfulResponseFor(url),
        ) as never);
        render(<Settings />);

        expect(await screen.findByRole('alert')).toHaveTextContent('Could not load notification preferences.');
        expect(screen.queryByText('Email Summaries')).not.toBeInTheDocument();
        expect(screen.queryByText('Push Notifications (Queue Alerts)')).not.toBeInTheDocument();
        expect(screen.getByText('Chrome')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Update' })).toBeInTheDocument();
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('does not claim there are no active sessions when their GET fails', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => Promise.resolve(
            url === '/auth/me/'
                ? { data: profilePreferences }
                : url === '/auth/sessions/'
                    ? Promise.reject(new Error('Network unavailable'))
                    : { data: { results: [loginEvent] } },
        ) as never);
        render(<Settings />);

        expect(await screen.findByRole('alert')).toHaveTextContent('Could not load active sessions.');
        expect(screen.queryByText('No active sessions found.')).not.toBeInTheDocument();
        expect(screen.getByText('Email Summaries')).toBeInTheDocument();
        expect(screen.getByText('Push Notifications (Queue Alerts)')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Update' })).toBeInTheDocument();
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('keeps profile errors visible after a failed retry and clears them after success', async () => {
        let profileReads = 0;
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url !== '/auth/me/') return Promise.resolve(successfulResponseFor(url)) as never;
            profileReads += 1;
            if (profileReads < 3) return Promise.reject(new Error('Network unavailable')) as never;
            return Promise.resolve({ data: profilePreferences }) as never;
        });
        render(<Settings />);

        expect(await screen.findByRole('alert')).toHaveTextContent('Could not load notification preferences.');
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
        await waitFor(() => expect(profileReads).toBe(2));
        expect(screen.getByRole('alert')).toHaveTextContent('Could not load notification preferences.');

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
        expect(await screen.findByText('Email Summaries')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(screen.getByText('Chrome')).toBeInTheDocument();
        expect(vi.mocked(axiosPrivate.get).mock.calls.filter(([url]) => url === '/auth/me/')).toHaveLength(3);
        expect(vi.mocked(axiosPrivate.get).mock.calls.filter(([url]) => url === '/auth/sessions/')).toHaveLength(1);
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('recovers the session list without refetching preferences', async () => {
        let sessionReads = 0;
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url !== '/auth/sessions/') return Promise.resolve(successfulResponseFor(url)) as never;
            sessionReads += 1;
            return sessionReads === 1
                ? Promise.reject(new Error('Network unavailable')) as never
                : Promise.resolve({ data: { results: [activeSession] } }) as never;
        });
        render(<Settings />);

        expect(await screen.findByRole('alert')).toHaveTextContent('Could not load active sessions.');
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(await screen.findByText('Chrome')).toBeInTheDocument();
        expect(screen.queryByText('No active sessions found.')).not.toBeInTheDocument();
        expect(screen.getByText('Email Summaries')).toBeInTheDocument();
        expect(vi.mocked(axiosPrivate.get).mock.calls.filter(([url]) => url === '/auth/sessions/')).toHaveLength(2);
        expect(vi.mocked(axiosPrivate.get).mock.calls.filter(([url]) => url === '/auth/me/')).toHaveLength(1);
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('disables profile retry while its GET is pending', async () => {
        let resolveProfile: (value: unknown) => void = () => {};
        let profileReads = 0;
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url !== '/auth/me/') return Promise.resolve(successfulResponseFor(url)) as never;
            profileReads += 1;
            if (profileReads === 1) return Promise.reject(new Error('Network unavailable')) as never;
            return new Promise((resolve) => { resolveProfile = resolve; }) as never;
        });
        render(<Settings />);

        fireEvent.click(await screen.findByRole('button', { name: 'Try again' }));
        const pendingRetry = await screen.findByRole('button', { name: 'Trying again…' });
        expect(pendingRetry).toBeDisabled();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(4);
        expect(axiosPrivate.patch).not.toHaveBeenCalled();

        resolveProfile({ data: profilePreferences });
        expect(await screen.findByText('Email Summaries')).toBeInTheDocument();
    });

    it('disables session retry while its GET is pending', async () => {
        let resolveSessions: (value: unknown) => void = () => {};
        let sessionReads = 0;
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url !== '/auth/sessions/') return Promise.resolve(successfulResponseFor(url)) as never;
            sessionReads += 1;
            if (sessionReads === 1) return Promise.reject(new Error('Network unavailable')) as never;
            return new Promise((resolve) => { resolveSessions = resolve; }) as never;
        });
        render(<Settings />);

        fireEvent.click(await screen.findByRole('button', { name: 'Try again' }));
        const pendingRetry = await screen.findByRole('button', { name: 'Trying again…' });
        expect(pendingRetry).toBeDisabled();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(4);
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();

        resolveSessions({ data: { results: [activeSession] } });
        expect(await screen.findByText('Chrome')).toBeInTheDocument();
    });

    it('sends true when enabling push alerts and waits for the save before updating the toggle', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => Promise.resolve(
            url === '/auth/me/'
                ? { data: { ...profilePreferences, push_alerts: false } }
                : successfulResponseFor(url),
        ) as never);
        let resolvePatch: (value: unknown) => void = () => {};
        vi.mocked(axiosPrivate.patch).mockReturnValueOnce(new Promise((resolve) => {
            resolvePatch = resolve;
        }) as never);
        render(<Settings />);

        await screen.findByText('Push Notifications (Queue Alerts)');
        const toggle = getPushToggle();
        fireEvent.click(toggle);

        await waitFor(() => expect(axiosPrivate.patch).toHaveBeenCalledWith('/auth/me/', { push_alerts: true }));
        expect(toggle).toHaveClass('bg-slate-200');

        resolvePatch({ data: {} });
        await waitFor(() => expect(toggle).toHaveClass('bg-orange-500'));
    });

    it('sends false when disabling push alerts', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => Promise.resolve(
            url === '/auth/me/'
                ? { data: { ...profilePreferences, push_alerts: true } }
                : successfulResponseFor(url),
        ) as never);
        vi.mocked(axiosPrivate.patch).mockResolvedValueOnce({ data: {} } as never);
        render(<Settings />);

        await screen.findByText('Push Notifications (Queue Alerts)');
        const toggle = getPushToggle();
        expect(toggle).toHaveClass('bg-orange-500');
        fireEvent.click(toggle);

        await waitFor(() => expect(axiosPrivate.patch).toHaveBeenCalledWith('/auth/me/', { push_alerts: false }));
        await waitFor(() => expect(toggle).toHaveClass('bg-slate-200'));
    });

    it('keeps the push toggle unchanged when saving the new preference fails', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => Promise.resolve(
            url === '/auth/me/'
                ? { data: { ...profilePreferences, push_alerts: false } }
                : successfulResponseFor(url),
        ) as never);
        vi.mocked(axiosPrivate.patch).mockRejectedValueOnce(new Error('Network unavailable'));
        render(<Settings />);

        await screen.findByText('Push Notifications (Queue Alerts)');
        const toggle = getPushToggle();
        fireEvent.click(toggle);

        await waitFor(() => expect(axiosPrivate.patch).toHaveBeenCalledWith('/auth/me/', { push_alerts: true }));
        await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Failed to update push preferences.'));
        expect(toggle).toHaveClass('bg-slate-200');
    });
});
