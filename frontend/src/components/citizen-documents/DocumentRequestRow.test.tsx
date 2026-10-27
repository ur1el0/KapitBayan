import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DocumentRequestRow } from './DocumentRequestRow';
import type { DocumentRequest, PaymentRecipient } from './types';

// Mock usePrivateMediaUrl hook
vi.mock('../../hooks/usePrivateMediaUrl', () => ({
    usePrivateMediaUrl: vi.fn((path) => ({
        url: path ? 'blob:mock-proof-image' : null,
        isLoading: false,
        hasError: false,
    })),
}));

describe('DocumentRequestRow', () => {
    const mockRecipients: PaymentRecipient[] = [
        {
            id: 1,
            provider: 'GCASH',
            provider_label: 'GCash',
            display_name: 'Barangay GCash Hub',
            recipient_name: 'Treasurer Juan',
            recipient_identifier: '09171234567',
            instructions: 'Send exact fee.',
        },
    ];

    const baseRequest: DocumentRequest = {
        id: 101,
        document_type: 'Barangay Clearance',
        purpose: 'Employment requirement',
        status: 'READY_FOR_PICKUP',
        fee_amount: 50.00,
        payment_method: '',
        payment_status: 'UNPAID',
        created_at: '2026-10-10T08:00:00.000Z',
    };

    const defaultProps = {
        request: baseRequest,
        recipients: mockRecipients,
        recipientsLoading: false,
        recipientsLoadError: false,
        onRetryRecipients: vi.fn(),
        onChoosePaymentMethod: vi.fn(),
        submittingPayment: false,
        downloading: false,
        cancelling: false,
        requestingCounterTicket: false,
        onSubmitPaymentReference: vi.fn(),
        onDownloadPdf: vi.fn(),
        onCancel: vi.fn(),
        onGetCounterTicket: vi.fn(),
    };

    beforeEach(() => {
        vi.clearAllMocks();
        window.URL.createObjectURL = vi.fn(() => 'blob:mock-preview-url');
        window.URL.revokeObjectURL = vi.fn();
    });

    const renderInTable = (ui: React.ReactElement) => {
        return render(
            <table>
                <tbody>{ui}</tbody>
            </table>,
        );
    };

    it('renders processing state guidance banner while status is PROCESSING with assessed fee', () => {
        const req: DocumentRequest = {
            ...baseRequest,
            status: 'PROCESSING',
            fee_amount: 50.00,
        };
        renderInTable(<DocumentRequestRow {...defaultProps} request={req} />);

        expect(screen.getByText('Document Under Processing')).toBeInTheDocument();
        expect(
            screen.getByText(/Assessment fee is ₱50.00. Official payment instructions and recipient details will become available once staff process and approve your document and mark it Ready for Pickup./i),
        ).toBeInTheDocument();
        expect(screen.queryByLabelText(/Payment recipient for request 101/i)).not.toBeInTheDocument();
    });

    it('renders cash instructions banner and hides online payment upload form when method is CASH', () => {
        const req: DocumentRequest = {
            ...baseRequest,
            status: 'READY_FOR_PICKUP',
            fee_amount: 75.00,
            payment_method: 'CASH',
            payment_status: 'UNPAID',
        };
        renderInTable(<DocumentRequestRow {...defaultProps} request={req} />);

        expect(screen.getByText('Payment Method: Cash')).toBeInTheDocument();
        expect(
            screen.getByText(/Please proceed to the Barangay Treasurer desk to pay ₱75.00 upon document pickup. No online upload required./i),
        ).toBeInTheDocument();
        expect(screen.queryByLabelText(/Payment recipient for request 101/i)).not.toBeInTheDocument();
    });

    it('renders statutory fee exemption badge for an exempt document type', () => {
        const req: DocumentRequest = {
            ...baseRequest,
            document_type: 'Certificate of Indigency',
            fee_amount: 0,
            payment_status: 'NOT_REQUIRED',
        };
        renderInTable(<DocumentRequestRow {...defaultProps} request={req} />);

        expect(
            screen.getByText(/Statutory Fee Exemption — No Payment Required \(RA 11261 \/ Indigency\)/i),
        ).toBeInTheDocument();
        expect(screen.queryByText(/Assessment: ₱/i)).not.toBeInTheDocument();
        expect(screen.queryByLabelText(/Payment recipient for request 101/i)).not.toBeInTheDocument();
    });

    it('does not call an ordinary unassessed request statutory fee exempt', () => {
        const req: DocumentRequest = {
            ...baseRequest,
            status: 'PROCESSING',
            fee_amount: 0,
            payment_status: 'NOT_REQUIRED',
        };
        renderInTable(<DocumentRequestRow {...defaultProps} request={req} />);

        expect(screen.getByText('Document Under Processing')).toBeInTheDocument();
        expect(screen.getByText(/fee is pending staff assessment/i)).toBeInTheDocument();
        expect(screen.queryByText(/Statutory Fee Exemption/i)).not.toBeInTheDocument();
        expect(screen.queryByLabelText(/Payment recipient for request 101/i)).not.toBeInTheDocument();
    });

    it('shows ordinary zero-fee requests as no payment required after assessment', () => {
        const req: DocumentRequest = {
            ...baseRequest,
            fee_amount: 0,
            payment_status: 'NOT_REQUIRED',
        };
        renderInTable(<DocumentRequestRow {...defaultProps} request={req} />);

        expect(screen.getByText('No payment required')).toBeInTheDocument();
        expect(screen.queryByText(/Statutory Fee Exemption/i)).not.toBeInTheDocument();
        expect(screen.queryByLabelText(/Payment recipient for request 101/i)).not.toBeInTheDocument();
    });

    it('renders pending verification banner with reference, timestamp, and proof preview button', () => {
        const req: DocumentRequest = {
            ...baseRequest,
            payment_status: 'PENDING_VERIFICATION',
            payment_method: 'GCASH',
            payment_recipient: 1,
            payment_reference: 'GC-REF-998877',
            payment_transacted_at: '2026-10-10T14:30:00.000Z',
            payment_proof_url: '/api/v1/document-requests/101/payment-proof/',
        };
        renderInTable(<DocumentRequestRow {...defaultProps} request={req} />);

        expect(screen.getByText(/Payment submitted and awaiting staff verification/i)).toBeInTheDocument();
        expect(screen.getByText('GC-REF-998877')).toBeInTheDocument();
        expect(screen.getByText(/Transacted at:/i)).toBeInTheDocument();

        const previewButton = screen.getByRole('button', { name: 'View submitted receipt' });
        expect(previewButton).toBeInTheDocument();

        // Clicking preview button opens the preview dialog
        fireEvent.click(previewButton);
        expect(screen.getByRole('dialog', { name: 'Payment receipt preview' })).toBeInTheDocument();
        expect(screen.getByAltText('Payment receipt proof')).toBeInTheDocument();

        // Closing the dialog
        fireEvent.click(screen.getByRole('button', { name: 'Close' }));
        expect(screen.queryByRole('dialog', { name: 'Payment receipt preview' })).not.toBeInTheDocument();
    });

    it('renders rejected payment banner with staff note and provides resubmit button to prefill retry form', () => {
        const req: DocumentRequest = {
            ...baseRequest,
            payment_status: 'REJECTED',
            payment_method: 'GCASH',
            payment_recipient: 1,
            payment_reference: 'GC-REJECTED-123',
            payment_transacted_at: '2026-10-10T12:00:00.000Z',
            payment_review_note: 'Screenshot does not match official account identifier.',
        };
        renderInTable(<DocumentRequestRow {...defaultProps} request={req} />);

        expect(screen.getByText('Payment Reference Rejected')).toBeInTheDocument();
        expect(
            screen.getByText(/Staff Note: Screenshot does not match official account identifier./i),
        ).toBeInTheDocument();

        const resubmitBtn = screen.getByRole('button', { name: 'Resubmit Payment Evidence' });
        expect(resubmitBtn).toBeInTheDocument();

        expect(screen.getByLabelText('Choose payment method')).toHaveValue('RECIPIENT:1');
        expect(screen.queryByLabelText(/Transfer reference for request 101/i)).not.toBeInTheDocument();

        fireEvent.click(resubmitBtn);

        // Form is now visible with prefilled values
        expect(screen.getByLabelText('Choose payment method')).toHaveValue('RECIPIENT:1');
        const refInput = screen.getByLabelText('Transfer reference for request 101') as HTMLInputElement;
        expect(refInput.value).toBe('GC-REJECTED-123');

        // Can cancel retry
        const cancelBtn = screen.getByRole('button', { name: 'Cancel' });
        fireEvent.click(cancelBtn);
        expect(screen.queryByLabelText(/Transfer reference for request 101/i)).not.toBeInTheDocument();
    });

    it('offers cash first and configured e-payment choices before showing the transfer form', () => {
        renderInTable(<DocumentRequestRow {...defaultProps} />);

        const methodSelect = screen.getByLabelText('Choose payment method') as HTMLSelectElement;
        expect(methodSelect).toHaveValue('');
        expect(methodSelect.options[1]).toHaveTextContent('Cash at barangay hall');
        expect(methodSelect.options[2]).toHaveTextContent('GCash · Barangay GCash Hub');
        expect(screen.queryByLabelText('Transfer reference for request 101')).not.toBeInTheDocument();

        fireEvent.change(methodSelect, { target: { value: 'RECIPIENT:1' } });
        expect(defaultProps.onChoosePaymentMethod).toHaveBeenCalledWith('RECIPIENT:1');
    });

    it('triggers cancel clearance request callback when status is PENDING', () => {
        const req: DocumentRequest = {
            ...baseRequest,
            status: 'PENDING',
        };
        renderInTable(<DocumentRequestRow {...defaultProps} request={req} />);

        const cancelBtn = screen.getByRole('button', { name: 'Cancel clearance request #101' });
        fireEvent.click(cancelBtn);

        expect(defaultProps.onCancel).toHaveBeenCalledTimes(1);
    });

    it('triggers download PDF callback when status is READY_FOR_PICKUP', () => {
        renderInTable(<DocumentRequestRow {...defaultProps} />);

        const downloadBtn = screen.getByRole('button', { name: 'Download PDF' });
        fireEvent.click(downloadBtn);

        expect(defaultProps.onDownloadPdf).toHaveBeenCalledTimes(1);
    });

    it('renders staff-approved waiver card with reason when fee_assessment_status is WAIVED', () => {
        const waivedReq: DocumentRequest = {
            ...baseRequest,
            status: 'READY_FOR_PICKUP',
            fee_amount: 0,
            fee_assessment_status: 'WAIVED',
            fee_waiver_reason: 'Medical mission assistance exemption',
            payment_status: 'NOT_REQUIRED',
        };
        renderInTable(<DocumentRequestRow {...defaultProps} request={waivedReq} />);

        expect(screen.getByText('Fee Waived (₱0.00) — Staff Approved')).toBeInTheDocument();
        expect(screen.getByText(/Reason:/)).toBeInTheDocument();
        expect(screen.getByText(/Medical mission assistance exemption/)).toBeInTheDocument();
        expect(screen.queryByLabelText(/Payment recipient for request 101/i)).not.toBeInTheDocument();
    });
});
