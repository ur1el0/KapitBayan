import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { BarangayApplications } from './BarangayApplications';

vi.mock('../../api/axios', () => ({ axiosPrivate: { get: vi.fn(), post: vi.fn() } }));

describe('BarangayApplications', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(axiosPrivate.get).mockReset();
        vi.mocked(axiosPrivate.post).mockReset();
        vi.spyOn(window, 'confirm').mockReturnValue(true);
        vi.mocked(axiosPrivate.get).mockResolvedValue({ data: [{
            id: 4, application_type: 'OFFICIAL', name: 'Barangay Mabini', municipality: 'Lucena City', province: 'Quezon',
            applicant_name: 'Maria Santos', applicant_position: 'Secretary',
            applicant_email: 'maria@example.com', applicant_phone: '09170000000',
            status: 'PENDING', review_note: '',
        }] } as never);
    });

    it('shows a loading status until the initial list request succeeds', async () => {
        let resolveLoad!: (response: { data: never[] }) => void;
        const pendingLoad = new Promise<{ data: never[] }>((resolve) => { resolveLoad = resolve; });
        vi.mocked(axiosPrivate.get).mockReturnValueOnce(pendingLoad as never);

        render(<BarangayApplications />);

        expect(screen.getByRole('status')).toHaveTextContent('Loading applications…');
        expect(screen.queryByText('No applications have been submitted.')).not.toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();

        await act(async () => {
            resolveLoad({ data: [] });
            await pendingLoad;
        });

        expect(screen.getByText('No applications have been submitted.')).toBeInTheDocument();
    });

    it('shows a retryable list error instead of a false empty state and recovers without reviewing an application', async () => {
        vi.mocked(axiosPrivate.get)
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockResolvedValueOnce({ data: [{
                id: 4, name: 'Barangay Mabini', municipality: 'Lucena City', province: 'Quezon',
                applicant_name: 'Maria Santos', applicant_position: 'Secretary',
                applicant_email: 'maria@example.com', applicant_phone: '09170000000',
                status: 'PENDING', review_note: '',
            }] } as never);

        render(<BarangayApplications />);

        expect(await screen.findByRole('alert')).toHaveTextContent('Could not load barangay applications.');
        expect(screen.getByRole('heading', { name: 'Official Account Applications' })).toBeInTheDocument();
        expect(screen.getByText(/Verify each official through official channels/)).toBeInTheDocument();
        expect(screen.queryByText('No applications have been submitted.')).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(await screen.findByRole('heading', { name: /Maria Santos/ })).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(1, '/auth/barangay-applications/');
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(2, '/auth/barangay-applications/');
        expect(axiosPrivate.post).not.toHaveBeenCalled();
    });

    it('keeps repeated failures retryable, disables retry while pending, then shows a genuine empty result', async () => {
        let rejectRetry!: (reason?: unknown) => void;
        const pendingRetry = new Promise<never>((_resolve, reject) => { rejectRetry = reject; });
        vi.mocked(axiosPrivate.get)
            .mockRejectedValueOnce(new Error('First failure'))
            .mockReturnValueOnce(pendingRetry as never)
            .mockResolvedValueOnce({ data: [] } as never);

        render(<BarangayApplications />);

        expect(await screen.findByRole('alert')).toHaveTextContent('Could not load barangay applications.');
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
        expect(screen.getByRole('button', { name: 'Trying again…' })).toBeDisabled();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(2);

        await act(async () => {
            rejectRetry(new Error('Still unavailable'));
            await pendingRetry.catch(() => undefined);
        });

        expect(await screen.findByRole('button', { name: 'Try again' })).toBeEnabled();
        expect(screen.getByRole('alert')).toHaveTextContent('Could not load barangay applications.');
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(await screen.findByText('No applications have been submitted.')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(3);
        expect(axiosPrivate.post).not.toHaveBeenCalled();
    });

    it('shows the empty state only after a successful empty response', async () => {
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({ data: [] } as never);

        render(<BarangayApplications />);

        expect(await screen.findByText('No applications have been submitted.')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('requires review decision confirmation and posts approval', async () => {
        vi.mocked(axiosPrivate.post).mockResolvedValue({ data: { id: 4, status: 'APPROVED' } } as never);
        render(<BarangayApplications />);
        fireEvent.click(await screen.findByRole('button', { name: 'Approve official account' }));

        expect(window.confirm).toHaveBeenCalledWith('Approve the official account request for Maria Santos at Barangay Mabini?');
        await waitFor(() => expect(axiosPrivate.post).toHaveBeenCalledWith('/auth/barangay-applications/4/review/', {
            status: 'APPROVED', review_note: '',
        }));
    });

    it('keeps the rejection-note requirement and sends the entered note', async () => {
        vi.mocked(axiosPrivate.post).mockResolvedValue({ data: {
            id: 4, name: 'Barangay Mabini', municipality: 'Lucena City', province: 'Quezon',
            applicant_name: 'Maria Santos', applicant_position: 'Secretary',
            applicant_email: 'maria@example.com', applicant_phone: '09170000000',
            status: 'REJECTED', review_note: 'Verification could not be completed.',
        } } as never);

        render(<BarangayApplications />);

        const rejectButton = await screen.findByRole('button', { name: 'Reject' });
        expect(rejectButton).toBeDisabled();
        expect(axiosPrivate.post).not.toHaveBeenCalled();

        fireEvent.change(screen.getByPlaceholderText('Required for rejection; include the verification outcome.'), {
            target: { value: 'Verification could not be completed.' },
        });
        expect(rejectButton).toBeEnabled();
        fireEvent.click(rejectButton);

        await waitFor(() => expect(axiosPrivate.post).toHaveBeenCalledWith('/auth/barangay-applications/4/review/', {
            status: 'REJECTED', review_note: 'Verification could not be completed.',
        }));
    });
});
