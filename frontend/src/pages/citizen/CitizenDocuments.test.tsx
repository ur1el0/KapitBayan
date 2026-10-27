import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { CitizenDocuments } from './CitizenDocuments';

vi.mock('../../api/axios', () => ({
    axiosPrivate: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

const createDeferred = <T,>() => {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((resolvePromise, rejectPromise) => {
        resolve = resolvePromise;
        reject = rejectPromise;
    });
    return { promise, resolve, reject };
};

describe('CitizenDocuments', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(axiosPrivate.get).mockImplementation(async (url: string) => ({
            data: url === '/document-catalog/' ? [{
                id: 42,
                document_type: 'Certificate of Residency',
                requirements: ['Government ID or proof of residency'],
                published_fee_amount: '50.00',
                details: '',
                is_active: true,
            }] : url === '/payment-recipients/' ? [{
                id: 7,
                provider: 'MAYA',
                provider_label: 'Maya',
                display_name: 'Barangay Maya',
                recipient_name: 'Barangay Treasurer',
                recipient_identifier: '09170000000',
                instructions: 'Add the document request number.',
            }] : [{
                id: 15,
                document_type: 'Barangay Clearance',
                purpose: 'Employment',
                status: 'READY_FOR_PICKUP',
                fee_amount: '50.00',
                payment_method: '',
                payment_status: 'UNPAID',
                created_at: '2026-10-08T00:00:00Z',
            }],
        } as never));
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('saves the resident-selected barangay payment method before submitting transfer evidence', async () => {
        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({
            data: {
                id: 15,
                status: 'READY_FOR_PICKUP',
                fee_amount: '50.00',
                payment_method: 'MAYA',
                payment_recipient: 7,
                payment_status: 'UNPAID',
            },
        } as never).mockResolvedValueOnce({
            data: {
                id: 15,
                payment_method: 'MAYA',
                payment_recipient: 7,
                payment_reference: 'GC-REF-5512',
                payment_status: 'PENDING_VERIFICATION',
            },
        } as never);

        render(<CitizenDocuments />);
        const paymentMethod = await screen.findByLabelText('Choose payment method');
        fireEvent.change(paymentMethod, { target: { value: 'RECIPIENT:7' } });

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenNthCalledWith(
                1,
                '/document-requests/15/payment-choice/',
                { payment_recipient_id: 7 },
            );
        });

        const input = screen.getByLabelText('Transfer reference for request 15');
        fireEvent.change(input, { target: { value: 'GC-REF-5512' } });

        const file = new File(['fake-proof-content'], 'receipt.png', { type: 'image/png' });
        const fileInput = screen.getByLabelText('Payment proof screenshot for request 15');
        fireEvent.change(fileInput, { target: { files: [file] } });

        fireEvent.click(screen.getByRole('button', { name: 'Submit transfer reference' }));

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenNthCalledWith(
                2,
                '/document-requests/15/payment-reference/',
                expect.any(FormData),
                expect.objectContaining({
                    headers: { 'Content-Type': 'multipart/form-data' },
                }),
            );
        });
        const formData = vi.mocked(axiosPrivate.post).mock.calls[1][1] as FormData;
        expect(formData.get('payment_recipient_id')).toBe('7');
        expect(formData.get('payment_reference')).toBe('GC-REF-5512');
        expect(formData.get('payment_proof_image')).toBeTruthy();
        expect(formData.get('payment_transacted_at')).toBeTruthy();
    });

    it('keeps recipient failures separate from requests and retries only the recipient read', async () => {
        const initialRead = createDeferred<{ data: unknown }>();
        const failedRetry = createDeferred<{ data: unknown }>();
        const recoveredRead = createDeferred<{ data: unknown }>();
        const recipientReads = [initialRead, failedRetry, recoveredRead];
        let recipientReadCount = 0;

        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url === '/payment-recipients/') {
                return recipientReads[recipientReadCount++].promise as never;
            }
            return Promise.resolve({
                data: [{
                    id: 15,
                    document_type: 'Barangay Clearance',
                    purpose: 'Employment',
                    status: 'READY_FOR_PICKUP',
                    fee_amount: '50.00',
                    payment_method: '',
                    payment_status: 'UNPAID',
                    created_at: '2026-10-08T00:00:00Z',
                }],
            } as never);
        });

        render(<CitizenDocuments />);

        expect(await screen.findByText('Barangay Clearance')).toBeInTheDocument();
        expect(await screen.findByRole('status')).toHaveTextContent('Loading barangay e-payment options');
        expect(screen.queryByText(/has not configured an e-payment recipient/i)).not.toBeInTheDocument();

        initialRead.reject(new Error('recipient service unavailable'));
        const retryButton = await screen.findByRole('button', { name: 'Retry payment option loading' });
        expect(screen.getByRole('alert')).toHaveTextContent('Could not load your barangay e-payment options. Cash remains available.');
        expect(screen.queryByText(/has not configured an e-payment recipient/i)).not.toBeInTheDocument();

        fireEvent.click(retryButton);
        expect(await screen.findByRole('status')).toHaveTextContent('Loading barangay e-payment options');
        expect(screen.queryByRole('button', { name: 'Retry payment option loading' })).not.toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(3);

        failedRetry.reject(new Error('recipient service still unavailable'));
        const retryAgainButton = await screen.findByRole('button', { name: 'Retry payment option loading' });
        expect(screen.getByRole('alert')).toHaveTextContent('Could not load your barangay e-payment options. Cash remains available.');

        fireEvent.click(retryAgainButton);
        recoveredRead.resolve({
            data: [{
                id: 7,
                provider: 'MAYA',
                provider_label: 'Maya',
                display_name: 'Barangay Maya',
                recipient_name: 'Barangay Treasurer',
                recipient_identifier: '09170000000',
                instructions: 'Add the document request number.',
            }],
        });

        expect(await screen.findByLabelText('Choose payment method')).toBeInTheDocument();
        await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
        expect(screen.getByText('Barangay Clearance')).toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(4);
        const requestedUrls = vi.mocked(axiosPrivate.get).mock.calls.map(([url]) => url);
        expect(requestedUrls.filter((url) => url === '/payment-recipients/')).toHaveLength(3);
        expect(requestedUrls.filter((url) => url === '/document-requests/')).toHaveLength(1);
        expect(axiosPrivate.post).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('shows the in-person fallback only after a successful empty recipient response', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation(async (url: string) => ({
            data: url === '/payment-recipients/' ? [] : [{
                id: 15,
                document_type: 'Barangay Clearance',
                purpose: 'Employment',
                status: 'READY_FOR_PICKUP',
                fee_amount: '50.00',
                payment_method: '',
                payment_status: 'UNPAID',
                created_at: '2026-10-08T00:00:00Z',
            }],
        } as never));

        render(<CitizenDocuments />);

        expect(await screen.findByText(/No e-payment options are configured/i)).toBeInTheDocument();
        expect(screen.getByText('Barangay Clearance')).toBeInTheDocument();
        expect(screen.getByLabelText('Choose payment method')).toHaveValue('');
        expect(screen.getByRole('option', { name: 'Cash at barangay hall' })).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('submits a new clearance request from the request modal', async () => {
        vi.mocked(axiosPrivate.post).mockResolvedValue({ data: {} } as never);

        render(<CitizenDocuments />);
        fireEvent.click(screen.getByRole('button', { name: 'Request New Clearance' }));
        fireEvent.change(await screen.findByLabelText('Document Type'), {
            target: { value: '42' },
        });
        fireEvent.change(screen.getByLabelText('Purpose Statement'), {
            target: { value: '  Postal ID  ' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Submit Application' }));

        await waitFor(() => expect(axiosPrivate.post).toHaveBeenCalledWith(
            '/document-requests/',
            { document_type: 'Certificate of Residency', offering_id: 42, purpose: 'Postal ID' },
        ));
        await waitFor(() => expect(
            screen.queryByRole('heading', { name: 'Request a document' }),
        ).not.toBeInTheDocument());
    });

    it('confirms and cancels a pending clearance request', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation(async (url: string) => ({
            data: url === '/payment-recipients/' ? [] : [{
                id: 22,
                document_type: 'Certificate of Residency',
                purpose: 'School enrollment',
                status: 'PENDING',
                created_at: '2026-10-08T00:00:00Z',
            }],
        } as never));
        vi.mocked(axiosPrivate.delete).mockResolvedValue({} as never);
        const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);

        render(<CitizenDocuments />);
        fireEvent.click(await screen.findByRole('button', {
            name: 'Cancel clearance request #22',
        }));

        expect(confirm).toHaveBeenCalledWith(
            'Are you sure you want to cancel this pending clearance application?',
        );
        await waitFor(() => expect(axiosPrivate.delete).toHaveBeenCalledWith(
            '/document-requests/22/',
        ));
    });
});
