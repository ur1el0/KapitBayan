import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import {
    resendBarangayApplicationVerification,
    submitBarangayApplication,
    verifyBarangayApplicationEmail,
} from '../../api/barangayOnboarding';
import { BarangayOnboarding } from './BarangayOnboarding';
import { VerifyBarangayEmail } from './VerifyBarangayEmail';

vi.mock('../../api/barangayOnboarding', () => ({
    submitBarangayApplication: vi.fn(),
    resendBarangayApplicationVerification: vi.fn(),
    verifyBarangayApplicationEmail: vi.fn(),
}));

describe('Barangay onboarding verification', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.history.replaceState({}, '', '/verify-barangay-email?application=12#token=single-use-token');
        vi.mocked(submitBarangayApplication).mockResolvedValue({
            id: 12,
            status: 'PENDING',
            created_at: '2026-10-19T00:00:00Z',
        });
        vi.mocked(resendBarangayApplicationVerification).mockResolvedValue({
            detail: 'If this application is pending and needs email verification, a new link will be sent when eligible.',
        });
        vi.mocked(verifyBarangayApplicationEmail).mockResolvedValue({
            detail: 'Email verified. The application still requires DILG review.',
        });
    });

    it('submits the authority document and shows a private resend fallback', async () => {
        render(
            <MemoryRouter>
                <BarangayOnboarding />
            </MemoryRouter>,
        );

        fireEvent.change(screen.getByLabelText('Barangay name'), { target: { value: 'Barangay Sample' } });
        fireEvent.change(screen.getByLabelText('Municipality or city'), { target: { value: 'Tayabas City' } });
        fireEvent.change(screen.getByLabelText('Province'), { target: { value: 'Quezon' } });
        fireEvent.change(screen.getByLabelText('Official’s full name'), { target: { value: 'Sample Official' } });
        fireEvent.change(screen.getByLabelText('Official position'), { target: { value: 'Barangay Captain' } });
        fireEvent.change(screen.getByLabelText('Official email'), { target: { value: 'captain@example.test' } });
        fireEvent.change(screen.getByLabelText('Official contact number'), { target: { value: '09123456789' } });
        fireEvent.change(screen.getByLabelText('Proof of official authority'), {
            target: { files: [new File(['%PDF-1.4 proof'], 'authority.pdf', { type: 'application/pdf' })] },
        });
        fireEvent.change(screen.getByLabelText('Set password'), { target: { value: 'SafePassword123!' } });
        fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'SafePassword123!' } });
        fireEvent.click(screen.getByLabelText(/I am authorized to request/));
        fireEvent.click(screen.getByLabelText(/I consent to use the applicant/));
        const submitButton = screen.getByRole('button', { name: 'Submit for DILG review' });
        expect(submitButton).toBeEnabled();
        fireEvent.submit(submitButton.closest('form')!);

        expect(await screen.findByRole('heading', { name: 'Application submitted' })).toBeInTheDocument();
        expect(submitBarangayApplication).toHaveBeenCalledWith(expect.objectContaining({
            applicant_email: 'captain@example.test',
            proof_of_authority: expect.any(File),
        }));

        fireEvent.click(screen.getByRole('button', { name: 'Resend verification email' }));
        await waitFor(() => expect(resendBarangayApplicationVerification).toHaveBeenCalledWith(12, 'captain@example.test'));
        expect(await screen.findByText(/If this application is pending and needs email verification/)).toBeInTheDocument();
    });

    it('waits for an explicit button click before verifying and clears the token after success', async () => {
        render(
            <MemoryRouter initialEntries={['/verify-barangay-email?application=12#token=single-use-token']}>
                <VerifyBarangayEmail />
            </MemoryRouter>,
        );

        expect(verifyBarangayApplicationEmail).not.toHaveBeenCalled();
        fireEvent.click(screen.getByRole('button', { name: 'Verify email' }));
        await waitFor(() => expect(verifyBarangayApplicationEmail).toHaveBeenCalledWith(12, 'single-use-token'));
        expect(await screen.findByText(/application still requires DILG review/i)).toBeInTheDocument();
        expect(window.location.hash).toBe('');
    });
});
