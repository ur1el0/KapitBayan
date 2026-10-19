import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { StaffManagementSettings } from './StaffManagementSettings';

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        post: vi.fn(),
        patch: vi.fn(),
    },
}));

describe('StaffManagementSettings', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(axiosPrivate.get).mockResolvedValue({ data: [] } as never);
    });

    it('renders empty state when no staff members exist', async () => {
        render(<StaffManagementSettings />);
        expect(await screen.findByText('No field officials registered yet')).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Barangay Field Officials & Staff' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Register Field Official' })).toBeEnabled();
    });

    it('submits account details without a password and confirms setup instructions', async () => {
        const createdStaff = {
            id: 10,
            email: 'carding@barangay.gov.ph',
            first_name: 'Ricardo',
            last_name: 'Dalisay',
            full_name: 'Ricardo Dalisay',
            role: 'FIELD_OFFICIAL',
            is_active: true,
            date_joined: '2026-10-15T08:00:00Z',
            last_login: null,
        };
        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({ data: createdStaff } as never);

        render(<StaffManagementSettings />);
        await screen.findByText('No field officials registered yet');

        fireEvent.change(screen.getByLabelText('First Name'), { target: { value: 'Ricardo' } });
        fireEvent.change(screen.getByLabelText('Last Name'), { target: { value: 'Dalisay' } });
        fireEvent.change(screen.getByLabelText('Official Email (sign-in)'), { target: { value: 'carding@barangay.gov.ph' } });
        fireEvent.click(screen.getByRole('button', { name: 'Register Field Official' }));

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith('/auth/staff/', {
                first_name: 'Ricardo',
                last_name: 'Dalisay',
                email: 'carding@barangay.gov.ph',
            });
        });

        expect(await screen.findByText(/setup instructions are being sent to carding@barangay.gov.ph/i)).toBeInTheDocument();
        expect(screen.getByText('Ricardo Dalisay')).toBeInTheDocument();
        expect(screen.getByRole('alert')).toHaveTextContent('Setup instructions are being sent to carding@barangay.gov.ph.');
        expect(screen.getAllByText('carding@barangay.gov.ph')).toHaveLength(2);
        expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
    });

    it('renders existing staff and toggles active status', async () => {
        const staff = {
            id: 5,
            email: 'juan@barangay.gov.ph',
            first_name: 'Juan',
            last_name: 'Dela Cruz',
            full_name: 'Juan Dela Cruz',
            role: 'FIELD_OFFICIAL',
            is_active: true,
            date_joined: '2026-10-15T08:00:00Z',
            last_login: null,
        };
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({ data: [staff] } as never);
        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({
            data: { ...staff, is_active: false },
        } as never);

        render(<StaffManagementSettings />);
        expect(await screen.findByText('Juan Dela Cruz')).toBeInTheDocument();
        expect(screen.getByText('Active')).toBeInTheDocument();

        const deactivateBtn = screen.getByRole('button', { name: 'Deactivate' });
        fireEvent.click(deactivateBtn);

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith('/auth/staff/5/toggle-status/');
        });

        expect(await screen.findByText('Field Official juan@barangay.gov.ph is now inactive.')).toBeInTheDocument();
        expect(screen.getByText('Deactivated')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Activate' })).toBeInTheDocument();
    });

    it('shows a retryable load alert on network error', async () => {
        vi.mocked(axiosPrivate.get).mockRejectedValueOnce(new Error('Network error'));
        render(<StaffManagementSettings />);

        expect(await screen.findByRole('alert')).toHaveTextContent('Could not load field officials list.');
        expect(screen.queryByText('No field officials registered yet')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Register Field Official' })).toBeEnabled();
    });

    it('edits allowed profile fields and updates the displayed row from the response', async () => {
        const staff = {
            id: 15,
            email: 'juan@barangay.gov.ph',
            first_name: 'Juan',
            last_name: 'Dela Cruz',
            full_name: 'Juan Dela Cruz',
            role: 'FIELD_OFFICIAL',
            is_active: true,
            date_joined: '2026-10-15T08:00:00Z',
            last_login: null,
        };
        const updated = {
            ...staff,
            email: 'juan.new@barangay.gov.ph',
            first_name: 'Juan Miguel',
            full_name: 'Juan Miguel Dela Cruz',
        };
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({ data: [staff] } as never);
        vi.mocked(axiosPrivate.patch).mockResolvedValueOnce({ data: updated } as never);

        render(<StaffManagementSettings />);
        await screen.findByText('Juan Dela Cruz');
        fireEvent.click(screen.getByRole('button', { name: 'Edit Juan Dela Cruz' }));
        expect(screen.getByLabelText('First Name for Juan Dela Cruz')).toHaveFocus();

        fireEvent.change(screen.getByLabelText('First Name for Juan Dela Cruz'), { target: { value: 'Juan Miguel' } });
        fireEvent.change(screen.getByLabelText('Official Email (sign-in) for Juan Dela Cruz'), { target: { value: 'JUAN.NEW@BARANGAY.GOV.PH' } });
        fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }));

        await waitFor(() => {
            expect(axiosPrivate.patch).toHaveBeenCalledWith('/auth/staff/15/', {
                first_name: 'Juan Miguel',
                last_name: 'Dela Cruz',
                email: 'juan.new@barangay.gov.ph',
            });
        });
        expect(await screen.findByText('Juan Miguel Dela Cruz')).toBeInTheDocument();
        expect(screen.getAllByText('juan.new@barangay.gov.ph')).toHaveLength(2);
        expect(screen.getByRole('alert')).toHaveTextContent('Profile updated for juan@barangay.gov.ph.');
        expect(screen.queryByLabelText(/Official Email \(sign-in\) for/)).not.toBeInTheDocument();
    });

    it('discards staged profile changes on cancel without sending a request', async () => {
        const staff = {
            id: 16,
            email: 'maria@barangay.gov.ph',
            first_name: 'Maria',
            last_name: 'Santos',
            full_name: 'Maria Santos',
            role: 'FIELD_OFFICIAL',
            is_active: true,
            date_joined: '2026-10-15T08:00:00Z',
            last_login: null,
        };
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({ data: [staff] } as never);

        render(<StaffManagementSettings />);
        await screen.findByText('Maria Santos');
        fireEvent.click(screen.getByRole('button', { name: 'Edit Maria Santos' }));
        fireEvent.change(screen.getByLabelText('First Name for Maria Santos'), { target: { value: 'Changed Draft' } });
        fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(screen.getByText('Maria Santos')).toBeInTheDocument();
        expect(screen.queryByText('Changed Draft')).not.toBeInTheDocument();
        expect(screen.queryByLabelText(/First Name for/)).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Edit Maria Santos' })).toHaveFocus();
    });

    it('keeps the editor open and announces a server error when saving fails', async () => {
        const staff = {
            id: 17,
            email: 'pedro@barangay.gov.ph',
            first_name: 'Pedro',
            last_name: 'Reyes',
            full_name: 'Pedro Reyes',
            role: 'FIELD_OFFICIAL',
            is_active: false,
            date_joined: '2026-10-15T08:00:00Z',
            last_login: null,
        };
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({ data: [staff] } as never);
        vi.mocked(axiosPrivate.patch).mockRejectedValueOnce({
            response: { data: { email: ['A user with that email address already exists.'] } },
        });

        render(<StaffManagementSettings />);
        await screen.findByText('Pedro Reyes');
        fireEvent.click(screen.getByRole('button', { name: 'Edit Pedro Reyes' }));
        fireEvent.change(screen.getByLabelText('Official Email (sign-in) for Pedro Reyes'), { target: { value: 'duplicate@example.com' } });
        fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }));

        expect(await screen.findByRole('alert')).toHaveTextContent('email: A user with that email address already exists.');
        expect(screen.getByLabelText('Official Email (sign-in) for Pedro Reyes')).toHaveValue('duplicate@example.com');
        expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    });
});
