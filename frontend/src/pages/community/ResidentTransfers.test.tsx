import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { ResidentTransfers } from './ResidentTransfers';

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        post: vi.fn(),
    },
}));

vi.mock('../../hooks/usePrivateMediaUrl', () => ({
    usePrivateMediaUrl: vi.fn((path) => ({
        url: path ? 'blob:mock-proof-url' : null,
        isLoading: false,
        hasError: false,
    })),
}));

describe('ResidentTransfers Component', () => {
    const mockTransfer = {
        id: 42,
        resident_id: 15,
        resident_name: 'Maria Clara',
        resident_username: 'mariac',
        source_barangay_id: 1,
        source_barangay_name: 'Barangay San Antonio',
        destination_barangay_id: 2,
        destination_barangay_name: 'Barangay San Isidro',
        purok: 'Purok 5',
        address_details: 'Unit 3A Villa Heights',
        has_proof_of_residency: true,
        reason: 'Moved to family property.',
        status: 'PENDING' as const,
        review_note: '',
        created_at: '2026-11-09T10:00:00Z',
        reviewed_at: null,
    };

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(axiosPrivate.get).mockResolvedValue({
            data: [mockTransfer],
        });
    });

    it('renders incoming transfer requests with applicant, source/destination, and residence details', async () => {
        render(<ResidentTransfers />);

        expect(await screen.findByText('Maria Clara')).toBeInTheDocument();
        expect(screen.getByText('Account: mariac')).toBeInTheDocument();
        expect(screen.getByText('Barangay San Antonio → Barangay San Isidro')).toBeInTheDocument();
        expect(screen.getByText('Purok 5, Unit 3A Villa Heights')).toBeInTheDocument();
        expect(screen.getByText('Moved to family property.')).toBeInTheDocument();
    });

    it('toggles residency proof image viewer when requested', async () => {
        render(<ResidentTransfers />);

        await screen.findByText('Maria Clara');
        const viewButton = screen.getByRole('button', { name: 'View uploaded residency proof' });
        expect(viewButton).toBeInTheDocument();

        fireEvent.click(viewButton);

        const img = await screen.findByAltText('Uploaded proof of residency');
        expect(img).toBeInTheDocument();
        expect(img).toHaveAttribute('src', 'blob:mock-proof-url');
        expect(screen.getByRole('button', { name: 'Hide residency proof' })).toBeInTheDocument();
    });

    it('enforces independent verification checkbox before allowing approval', async () => {
        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({ data: {} });

        render(<ResidentTransfers />);

        await screen.findByText('Maria Clara');
        const approveButton = screen.getByRole('button', { name: /Approve transfer/i }) as HTMLButtonElement;
        expect(approveButton).toBeDisabled();

        const checkbox = screen.getByRole('checkbox');
        fireEvent.click(checkbox);

        expect(approveButton).not.toBeDisabled();

        fireEvent.click(approveButton);

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith(
                '/auth/resident-transfers/42/approve/',
                { residency_confirmed: true }
            );
        });
    });

    it('requires a rejection reason before rejecting transfer', async () => {
        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({ data: {} });

        render(<ResidentTransfers />);

        await screen.findByText('Maria Clara');
        const rejectButton = screen.getByRole('button', { name: /Reject request/i });

        // Click reject without reason
        fireEvent.click(rejectButton);

        expect(axiosPrivate.post).not.toHaveBeenCalled();
        expect(await screen.findByRole('alert')).toHaveTextContent(
            "Enter a reason before rejecting Maria Clara's transfer."
        );

        // Enter reason
        const reasonInput = screen.getByLabelText(/Rejection reason/i);
        fireEvent.change(reasonInput, { target: { value: 'Proof document is illegible.' } });

        fireEvent.click(rejectButton);

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith(
                '/auth/resident-transfers/42/reject/',
                { review_note: 'Proof document is illegible.' }
            );
        });
    });

    it('renders empty message when no transfer requests exist', async () => {
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({ data: [] });

        render(<ResidentTransfers />);

        expect(await screen.findByText('No transfer requests have been submitted to this Barangay.')).toBeInTheDocument();
    });
});
