import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { useAuth } from '../../context/auth-context';
import { ResidentProfileSettings } from './ResidentProfileSettings';

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        patch: vi.fn(),
        post: vi.fn(),
    },
}));

vi.mock('../../context/auth-context', () => ({
    useAuth: vi.fn(),
}));

describe('ResidentProfileSettings - Barangay Transfer Flow', () => {
    const mockUser = {
        id: 10,
        username: 'juandc',
        email: 'juan@example.com',
        full_name: 'Juan Dela Cruz',
        role: 'RESIDENT',
        barangay_id: 1,
        barangay_name: 'Barangay San Antonio',
        email_alerts: true,
        push_alerts: true,
        profile: {
            id: 20,
            full_name: 'Juan Dela Cruz',
            contact_number: '09171234567',
            birth_date: '1990-01-01',
            voter_status: true,
            is_verified: true,
            purok: 'Purok 1',
            address_details: 'Old St, San Antonio',
        },
    };

    const mockBarangays = [
        { id: 1, name: 'Barangay San Antonio' },
        { id: 2, name: 'Barangay San Isidro' },
        { id: 3, name: 'Barangay Santa Cruz' },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useAuth).mockReturnValue({
            user: mockUser,
            updateUser: vi.fn(),
        } as never);

        vi.mocked(axiosPrivate.get).mockImplementation(async (url: string) => {
            if (url === '/auth/me/') {
                return { data: mockUser };
            }
            if (url === '/auth/public/barangays/') {
                return { data: mockBarangays };
            }
            if (url === '/auth/resident-transfers/') {
                return { data: [] };
            }
            return { data: {} };
        });
    });

    it('renders the transfer form for verified residents excluding current barangay', async () => {
        render(<ResidentProfileSettings />);

        const select = (await screen.findByLabelText(/Receiving Barangay/i)) as HTMLSelectElement;
        expect(select).toBeInTheDocument();
        expect(screen.getByText('Barangay San Isidro')).toBeInTheDocument();
        expect(screen.getByText('Barangay Santa Cruz')).toBeInTheDocument();
        expect(screen.queryByRole('option', { name: 'Barangay San Antonio' })).not.toBeInTheDocument();

        // Fields should be present
        expect(screen.getByLabelText(/Purok \/ Zone/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/New Street Address \/ Details/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Proof of Residency/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Reason for moving/i)).toBeInTheDocument();
    });

    it('rejects proof files larger than 5 MiB on client side', async () => {
        render(<ResidentProfileSettings />);

        const fileInput = (await screen.findByLabelText(/Proof of Residency/i)) as HTMLInputElement;
        const largeFile = new File(['a'.repeat(6 * 1024 * 1024)], 'large_bill.png', { type: 'image/png' });

        fireEvent.change(fileInput, { target: { files: [largeFile] } });

        expect(await screen.findByRole('alert')).toHaveTextContent(
            'Residency proof image must be 5 MiB or smaller.'
        );
        expect(fileInput.value).toBe('');
    });

    it('submits a valid transfer request as multipart/form-data', async () => {
        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({
            data: {
                id: 101,
                destination_barangay_id: 2,
                reason: 'Relocated near workplace.',
                status: 'PENDING',
            },
        });

        render(<ResidentProfileSettings />);

        const select = await screen.findByLabelText(/Receiving Barangay/i);
        fireEvent.change(select, { target: { value: '2' } });
        fireEvent.change(screen.getByLabelText(/Purok \/ Zone/i), { target: { value: 'Purok 4' } });
        fireEvent.change(screen.getByLabelText(/New Street Address \/ Details/i), { target: { value: '456 Mabini St' } });
        fireEvent.change(screen.getByLabelText(/Reason for moving/i), { target: { value: 'Relocated near workplace.' } });

        const validFile = new File(['valid_image_bytes'], 'lease_contract.jpg', { type: 'image/jpeg' });
        fireEvent.change(screen.getByLabelText(/Proof of Residency/i), { target: { files: [validFile] } });

        const submitButton = screen.getByRole('button', { name: 'Submit transfer request' });
        fireEvent.submit(submitButton.closest('form')!);

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith(
                '/auth/resident-transfers/',
                expect.any(FormData),
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );
        });

        expect(await screen.findByText('Transfer request sent to the receiving Barangay for verification.')).toBeInTheDocument();
    });

    it('blocks new submissions and displays pending message when user has an active request', async () => {
        const pendingTransfer = {
            id: 88,
            source_barangay_name: 'Barangay San Antonio',
            destination_barangay_name: 'Barangay San Isidro',
            purok: 'Purok 4',
            address_details: '456 Mabini St',
            has_proof_of_residency: true,
            reason: 'Relocated to new house.',
            status: 'PENDING',
            review_note: '',
            created_at: '2026-11-09T10:00:00Z',
        };

        vi.mocked(axiosPrivate.get).mockImplementation(async (url: string) => {
            if (url === '/auth/me/') return { data: mockUser };
            if (url === '/auth/public/barangays/') return { data: mockBarangays };
            if (url === '/auth/resident-transfers/') return { data: [pendingTransfer] };
            return { data: {} };
        });

        render(<ResidentProfileSettings />);

        expect(await screen.findByText('You already have a transfer request waiting for review. You can submit another after it is approved or rejected.')).toBeInTheDocument();

        // The form should not be rendered
        expect(screen.queryByRole('button', { name: 'Submit transfer request' })).not.toBeInTheDocument();

        // History item should be visible with status
        expect(screen.getByText('Barangay San Antonio → Barangay San Isidro')).toBeInTheDocument();
        expect(screen.getByText('PENDING')).toBeInTheDocument();
        expect(screen.getByText(/Purok 4, 456 Mabini St/)).toBeInTheDocument();
    });

    it('shows rejection reason in history when a previous transfer was rejected', async () => {
        const rejectedTransfer = {
            id: 89,
            source_barangay_name: 'Barangay San Antonio',
            destination_barangay_name: 'Barangay San Isidro',
            purok: 'Purok 9',
            address_details: 'Unverified address',
            has_proof_of_residency: true,
            reason: 'Moving to San Isidro.',
            status: 'REJECTED',
            review_note: 'Utility bill address did not match Purok records.',
            created_at: '2026-11-08T09:00:00Z',
        };

        vi.mocked(axiosPrivate.get).mockImplementation(async (url: string) => {
            if (url === '/auth/me/') return { data: mockUser };
            if (url === '/auth/public/barangays/') return { data: mockBarangays };
            if (url === '/auth/resident-transfers/') return { data: [rejectedTransfer] };
            return { data: {} };
        });

        render(<ResidentProfileSettings />);

        expect(await screen.findByText('REJECTED')).toBeInTheDocument();
        expect(screen.getByText(/Utility bill address did not match Purok records/)).toBeInTheDocument();
    });
});
