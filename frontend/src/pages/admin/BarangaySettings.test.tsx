import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { useAuth } from '../../context/auth-context';
import { BarangaySettings } from './BarangaySettings';

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        patch: vi.fn(),
    },
}));

vi.mock('../../context/auth-context', () => ({
    useAuth: vi.fn(),
}));

const barangaySettings = {
    id: 12,
    name: 'Barangay Test',
    captain_name: 'Captain Test',
    office_contact: 'Barangay Hall',
    logo: null,
    city_seal: null,
    primary_color: '#082B66',
};

describe('BarangaySettings', () => {
    const updateBarangayPrimaryColor = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useAuth).mockReturnValue({
            user: null,
            login: vi.fn(),
            logout: vi.fn(async () => {}),
            isAuthenticated: true,
            updateBarangayPrimaryColor,
        });
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => Promise.resolve(
            url === '/auth/barangay/'
                ? { data: { results: [{ ...barangaySettings, captain_name: '', office_contact: '' }] } }
                : { data: [] },
        ) as never);
        vi.mocked(axiosPrivate.patch).mockResolvedValue({
            data: { primary_color: '#C70039' },
        } as never);
    });

    it('saves the selected primary color and updates the active theme', async () => {
        vi.mocked(useAuth).mockReturnValue({
            user: { role: 'ADMIN' },
            login: vi.fn(),
            logout: vi.fn(async () => {}),
            isAuthenticated: true,
            updateBarangayPrimaryColor,
        } as never);
        render(<BarangaySettings />);

        const colorInput = await screen.findByLabelText('Primary brand color');
        fireEvent.change(colorInput, { target: { value: '#c70039' } });
        fireEvent.click(screen.getByRole('button', { name: /save settings/i }));

        await waitFor(() => {
            expect(axiosPrivate.patch).toHaveBeenCalled();
            expect(updateBarangayPrimaryColor).toHaveBeenCalledWith('#C70039');
        });

        const formData = vi.mocked(axiosPrivate.patch).mock.calls[0]?.[1] as FormData;
        expect(formData.get('primary_color')).toBe('#C70039');
        expect(await screen.findByText('Settings updated successfully!')).toBeInTheDocument();
    });

    it('shows staff account management only to Barangay Admins', async () => {
        vi.mocked(useAuth).mockReturnValue({
            user: { role: 'ADMIN' },
            login: vi.fn(),
            logout: vi.fn(async () => {}),
            isAuthenticated: true,
            updateBarangayPrimaryColor,
        } as never);
        const { rerender } = render(<BarangaySettings />);
        expect(await screen.findByRole('heading', { name: 'Barangay Field Officials & Staff' })).toBeInTheDocument();

        vi.mocked(useAuth).mockReturnValue({
            user: { role: 'BARANGAY_OPERATOR' },
            login: vi.fn(),
            logout: vi.fn(async () => {}),
            isAuthenticated: true,
            updateBarangayPrimaryColor,
        } as never);
        rerender(<BarangaySettings />);
        expect(screen.queryByRole('heading', { name: 'Barangay Field Officials & Staff' })).not.toBeInTheDocument();
    });

    it('shows a retryable settings error and preserves payment recipient settings', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => Promise.resolve(
            url === '/auth/barangay/'
                ? Promise.reject(new Error('Network unavailable'))
                : { data: [] },
        ) as never);
        render(<BarangaySettings />);

        expect(await screen.findByRole('alert')).toHaveTextContent('Could not load barangay settings.');
        expect(screen.getByRole('heading', { name: 'Barangay Identity Settings' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Electronic payment recipients' })).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Save Settings' })).not.toBeInTheDocument();
        expect(screen.queryByLabelText('Primary brand color')).not.toBeInTheDocument();
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
    });

    it('does not show a blank identity form when the settings response has no barangay record', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => Promise.resolve(
            url === '/auth/barangay/'
                ? { data: { results: [] } }
                : { data: [] },
        ) as never);
        render(<BarangaySettings />);

        expect(await screen.findByRole('alert')).toHaveTextContent('Could not load barangay settings.');
        expect(screen.queryByRole('button', { name: 'Save Settings' })).not.toBeInTheDocument();
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
    });

    it('keeps repeated retry errors visible and restores the form after a successful retry', async () => {
        let settingsReads = 0;
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url !== '/auth/barangay/') return Promise.resolve({ data: [] }) as never;
            settingsReads += 1;
            if (settingsReads < 3) return Promise.reject(new Error('Network unavailable')) as never;
            return Promise.resolve({ data: { results: [barangaySettings] } }) as never;
        });
        render(<BarangaySettings />);

        expect(await screen.findByRole('alert')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
        await waitFor(() => expect(settingsReads).toBe(2));
        expect(screen.getByRole('alert')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
        expect(await screen.findByLabelText('Primary brand color')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(screen.getByDisplayValue('Barangay Test')).toHaveValue('Barangay Test');
        expect(screen.getByDisplayValue('Captain Test')).toHaveValue('Captain Test');
        expect(settingsReads).toBe(3);
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
    });

    it('disables retry while the barangay settings GET is pending', async () => {
        let settingsReads = 0;
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url !== '/auth/barangay/') return Promise.resolve({ data: [] }) as never;
            settingsReads += 1;
            return settingsReads === 1
                ? Promise.reject(new Error('Network unavailable')) as never
                : new Promise(() => {});
        });
        render(<BarangaySettings />);

        await screen.findByRole('alert');
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(await screen.findByRole('button', { name: 'Trying again…' })).toBeDisabled();
        expect(settingsReads).toBe(2);
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
    });
});
