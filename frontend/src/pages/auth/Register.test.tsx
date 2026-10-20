import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { axiosPublic } from '../../api/axios';
import { Register } from './Register';

beforeEach(() => {
    vi.spyOn(axiosPublic, 'get').mockResolvedValue({
        data: [{ id: 2, name: 'Barangay Ibabang Dupay', municipality: 'Lucena City', province: 'Quezon' }],
    } as never);
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('Resident Register Component', () => {
    it('renders Resident Registration by default with resident fields and LGU service highlights', () => {
        render(
            <BrowserRouter>
                <Register />
            </BrowserRouter>
        );

        // Branding & Citizen Badges
        expect(screen.getByText('KapitBayan')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /switch to/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('link', { name: /official registration/i })).not.toBeInTheDocument();
        expect(screen.getByText('Barangay services and clearances')).toBeInTheDocument();
        expect(screen.getByText('Queue updates')).toBeInTheDocument();
        expect(screen.getByText('Community program updates')).toBeInTheDocument();

        // Right form headings
        expect(screen.getByRole('heading', { level: 2, name: 'Resident Registration' })).toBeInTheDocument();
        expect(screen.getByText('Complete your registration details to access barangay services.')).toBeInTheDocument();

        // Citizen Inputs
        expect(screen.getByPlaceholderText('e.g. Juan Dela Cruz')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('juandelacruz')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('juan@example.com')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('0917 123 4567')).toBeInTheDocument();
        expect(screen.getAllByPlaceholderText('••••••••')).toHaveLength(2);

        // Submit Button & Navigation
        expect(screen.getByRole('button', { name: /create resident account/i })).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /log in here/i })).toHaveAttribute('href', '/login');
    });

    it('blocks registration when the approved barangay directory is unavailable', async () => {
        vi.mocked(axiosPublic.get).mockRejectedValueOnce(new Error('offline'));
        render(
            <BrowserRouter>
                <Register />
            </BrowserRouter>
        );

        expect(await screen.findByRole('alert')).toHaveTextContent('Approved barangays could not be loaded');
        fireEvent.click(screen.getByRole('checkbox'));
        expect(screen.getByRole('button', { name: /create resident account/i })).toBeDisabled();
    });

    it('retries a failed barangay directory lookup until it recovers without submitting registration', async () => {
        const getSpy = vi.mocked(axiosPublic.get);
        const postSpy = vi.spyOn(axiosPublic, 'post').mockResolvedValue({ data: {} } as never);
        let rejectRetry!: (reason: Error) => void;
        getSpy
            .mockRejectedValueOnce(new Error('offline'))
            .mockImplementationOnce(
                () => new Promise((_resolve, reject) => { rejectRetry = reject; }),
            )
            .mockResolvedValueOnce({
                data: [{ id: 2, name: 'Barangay Ibabang Dupay', municipality: 'Lucena City', province: 'Quezon' }],
            } as never);

        render(
            <BrowserRouter>
                <Register />
            </BrowserRouter>,
        );

        expect(await screen.findByRole('alert')).toHaveTextContent('Approved barangays could not be loaded');
        const selector = screen.getByRole('combobox');
        expect(selector).toBeDisabled();

        const retryButton = screen.getByRole('button', { name: 'Retry approved barangay list' });
        fireEvent.click(retryButton);
        await waitFor(() => expect(retryButton).toBeDisabled());
        expect(retryButton).toHaveClass('min-h-[44px]', 'min-w-[44px]', 'focus-visible:ring-2');
        expect(screen.getByRole('status')).toHaveTextContent('Retrying approved barangay list');

        await act(async () => {
            rejectRetry(new Error('offline again'));
        });

        expect(await screen.findByRole('alert')).toHaveTextContent('Approved barangays could not be loaded');
        expect(screen.getByRole('button', { name: 'Retry approved barangay list' })).toBeEnabled();
        fireEvent.click(screen.getByRole('button', { name: 'Retry approved barangay list' }));

        expect(await screen.findByRole('option', { name: /Barangay Ibabang Dupay/ })).toBeInTheDocument();
        expect(selector).toBeEnabled();
        expect(getSpy).toHaveBeenCalledTimes(3);
        expect(getSpy.mock.calls.map(([url]) => url)).toEqual([
            '/auth/public/barangays/',
            '/auth/public/barangays/',
            '/auth/public/barangays/',
        ]);
        expect(postSpy).not.toHaveBeenCalled();
    });

    it('makes a malformed barangay directory response retryable', async () => {
        const getSpy = vi.mocked(axiosPublic.get);
        getSpy
            .mockResolvedValueOnce({ data: { results: 'invalid' } } as never)
            .mockResolvedValueOnce({
                data: [{ id: 2, name: 'Barangay Ibabang Dupay', municipality: 'Lucena City', province: 'Quezon' }],
            } as never);

        render(
            <BrowserRouter>
                <Register />
            </BrowserRouter>,
        );

        expect(await screen.findByRole('alert')).toHaveTextContent('Approved barangays could not be loaded');
        fireEvent.click(screen.getByRole('button', { name: 'Retry approved barangay list' }));
        expect(await screen.findByRole('option', { name: /Barangay Ibabang Dupay/ })).toBeInTheDocument();
        expect(getSpy).toHaveBeenCalledTimes(2);
    });

    it('validates password mismatch before submission', async () => {
        render(
            <BrowserRouter>
                <Register />
            </BrowserRouter>
        );

        const fullNameInput = screen.getByPlaceholderText('e.g. Juan Dela Cruz');
        const usernameInput = screen.getByPlaceholderText('juandelacruz');
        const emailInput = screen.getByPlaceholderText('juan@example.com');
        const [passwordInput, confirmPasswordInput] = screen.getAllByPlaceholderText('••••••••');
        const submitButton = screen.getByRole('button', { name: /create resident account/i });

        fireEvent.change(fullNameInput, { target: { value: 'Juan Dela Cruz' } });
        fireEvent.change(usernameInput, { target: { value: 'juandc' } });
        fireEvent.change(emailInput, { target: { value: 'juan@test.com' } });
        fireEvent.change(passwordInput, { target: { value: 'Password123!' } });
        fireEvent.change(confirmPasswordInput, { target: { value: 'DifferentPassword!' } });

        // Dispatch submit directly to trigger the component's onSubmit handler
        fireEvent.submit(submitButton.closest('form')!);

        expect(await screen.findByText('Passwords do not match.')).toBeInTheDocument();
    });

    it('sends accepted privacy consent with resident registration', async () => {
        const postSpy = vi
            .spyOn(axiosPublic, 'post')
            .mockResolvedValue({ data: {} } as never);

        render(
            <BrowserRouter>
                <Register />
            </BrowserRouter>
        );

        fireEvent.change(screen.getByPlaceholderText('e.g. Juan Dela Cruz'), {
            target: { value: 'Juan Dela Cruz' },
        });
        fireEvent.change(screen.getByPlaceholderText('juandelacruz'), {
            target: { value: 'juandc' },
        });
        fireEvent.change(screen.getByPlaceholderText('juan@example.com'), {
            target: { value: 'juan@example.com' },
        });
        fireEvent.change(screen.getByPlaceholderText('e.g. Purok 3 or Zone 2'), {
            target: { value: 'Purok 3' },
        });
        await screen.findByRole('option', { name: /Barangay Ibabang Dupay/ });
        fireEvent.change(screen.getByRole('combobox'), {
            target: { value: '2' },
        });

        const [passwordInput, confirmPasswordInput] =
            screen.getAllByPlaceholderText('••••••••');
        fireEvent.change(passwordInput, {
            target: { value: 'Password123!' },
        });
        fireEvent.change(confirmPasswordInput, {
            target: { value: 'Password123!' },
        });

        const birthDateInput =
            document.querySelector<HTMLInputElement>('input[type="date"]');
        expect(birthDateInput).not.toBeNull();
        fireEvent.change(birthDateInput!, {
            target: { value: '1990-01-01' },
        });

        fireEvent.click(screen.getByRole('button', { name: /identity & residency verification/i }));
        const idPhoto = new File(['resident id'], 'resident-id.png', { type: 'image/png' });
        const fileInput = document.querySelector<HTMLInputElement>('input[type="file"]');
        expect(fileInput).not.toBeNull();
        fireEvent.change(fileInput!, { target: { files: [idPhoto] } });

        fireEvent.click(screen.getByRole('checkbox'));
        fireEvent.submit(
            screen
                .getByRole('button', { name: /create resident account/i })
                .closest('form')!
        );

        await waitFor(() => {
            expect(postSpy).toHaveBeenCalled();
        });

        const [url, payload] = postSpy.mock.calls[0];
        expect(url).toBe('/auth/register/');
        expect(payload).toBeInstanceOf(FormData);

        const formData = payload as FormData;
        expect(formData.get('privacy_consent')).toBe('true');
        expect(formData.get('privacy_consent_version')).toBe('resident-v1');
        expect(formData.get('barangay_id')).toBe('2');
        expect(formData.get('purok')).toBe('Purok 3');
        expect(formData.get('philsys_id_photo')).toBe(idPhoto);
    });

    it('requires an ID or residency proof upload before resident registration', async () => {
        const postSpy = vi
            .spyOn(axiosPublic, 'post')
            .mockResolvedValue({ data: {} } as never);

        render(
            <BrowserRouter>
                <Register />
            </BrowserRouter>
        );

        const [passwordInput, confirmPasswordInput] =
            screen.getAllByPlaceholderText('••••••••');
        fireEvent.change(passwordInput, { target: { value: 'Password123!' } });
        fireEvent.change(confirmPasswordInput, { target: { value: 'Password123!' } });
        fireEvent.change(screen.getByPlaceholderText('e.g. Purok 3 or Zone 2'), {
            target: { value: 'Purok 3' },
        });
        await screen.findByRole('option', { name: /Barangay Ibabang Dupay/ });
        fireEvent.click(screen.getByRole('checkbox'));

        fireEvent.submit(
            screen
                .getByRole('button', { name: /create resident account/i })
                .closest('form')!
        );

        expect(
            await screen.findByText('Upload at least one ID or proof of residency photo to register.')
        ).toBeInTheDocument();
        expect(
            screen.getByRole('button', { name: /identity & residency verification/i })
        ).toHaveAttribute('aria-expanded', 'true');
        expect(postSpy).not.toHaveBeenCalled();
    });
});
