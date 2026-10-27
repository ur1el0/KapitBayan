import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import toast from 'react-hot-toast';
import { ReviewDocumentModal } from './ReviewDocumentModal';
import type { DocumentRequest } from '../../pages/services/DocumentRequests';

vi.mock('../../hooks/usePrivateMediaUrl', () => ({
    usePrivateMediaUrl: vi.fn((path) => ({
        url: path ? 'blob:mock-receipt-image' : null,
        isLoading: false,
        hasError: false,
    })),
}));

vi.mock('react-hot-toast', () => ({
    default: {
        error: vi.fn(),
        success: vi.fn(),
    },
}));

describe('ReviewDocumentModal', () => {
    const baseRequest: DocumentRequest = {
        id: 42,
        requester_name: 'Juan Dela Cruz',
        purok: 'Purok 1',
        document_type: 'Barangay Clearance',
        purpose: 'Employment requirement',
        status: 'READY_FOR_PICKUP',
        fee_amount: 50.00,
        payment_method: 'GCASH',
        payment_status: 'PENDING_VERIFICATION',
        payment_reference: 'GCASH-REF-891011',
        payment_transacted_at: '2026-10-13T10:30:00Z',
        payment_recipient_name_snapshot: 'Barangay Treasury Fund',
        payment_recipient_identifier_snapshot: '0917-000-1111',
        payment_instructions_snapshot: 'Send exact fee to official treasury number.',
        payment_proof_url: '/api/v1/document-requests/42/payment-proof/',
        created_at: '2026-10-13T08:00:00Z',
    };

    const defaultProps = {
        selectedRequest: baseRequest,
        closeModal: vi.fn(),
        getStatusBadge: vi.fn(() => 'bg-purple-100 text-purple-800'),
        handleStatusUpdate: vi.fn(),
        handlePaymentReview: vi.fn(),
        handleSaveOrNumber: vi.fn(),
        isUpdating: false,
        handleDownloadPDF: vi.fn(),
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders electronic payment metadata, recipient snapshots, and staff guidance', () => {
        render(<ReviewDocumentModal {...defaultProps} />);

        expect(screen.getByText('GCASH Transfer Details')).toBeInTheDocument();
        expect(screen.getByText('GCASH-REF-891011')).toBeInTheDocument();
        expect(screen.getByText(/Barangay Treasury Fund · 0917-000-1111/)).toBeInTheDocument();
        expect(screen.getByText(/Send exact fee to official treasury number\./)).toBeInTheDocument();
        expect(screen.getByText(/Staff Verification Guidance:/)).toBeInTheDocument();
        expect(screen.getByText(/match your official barangay receiving account before verifying/)).toBeInTheDocument();
    });

    it('renders receipt preview and opens zoom inspection modal', () => {
        render(<ReviewDocumentModal {...defaultProps} />);

        const inspectBtn = screen.getByRole('button', { name: /inspect receipt/i });
        expect(inspectBtn).toBeInTheDocument();

        fireEvent.click(inspectBtn);

        const zoomDialog = screen.getByRole('dialog', { name: 'Inspect Payment Proof' });
        expect(zoomDialog).toBeInTheDocument();
        expect(screen.getByText(/Official Payment Receipt \(GCASH-REF-891011\)/)).toBeInTheDocument();

        const zoomInBtn = screen.getByRole('button', { name: 'Zoom in' });
        const zoomOutBtn = screen.getByRole('button', { name: 'Zoom out' });
        expect(zoomInBtn).toBeInTheDocument();
        expect(zoomOutBtn).toBeInTheDocument();

        fireEvent.click(zoomInBtn);
        expect(screen.getByText('125%')).toBeInTheDocument();

        const closeZoomBtn = screen.getByRole('button', { name: 'Close receipt inspection' });
        fireEvent.click(closeZoomBtn);
        expect(screen.queryByRole('dialog', { name: 'Inspect Payment Proof' })).not.toBeInTheDocument();
    });

    it('allows entering O.R. number and persists it independently without advancing status', () => {
        render(<ReviewDocumentModal {...defaultProps} />);

        const orInput = screen.getByPlaceholderText('e.g. OR-89104');
        fireEvent.change(orInput, { target: { value: 'OR-2026-9999' } });

        const saveOrBtn = screen.getByRole('button', { name: 'Save O.R.' });
        expect(saveOrBtn).toBeInTheDocument();

        fireEvent.click(saveOrBtn);
        expect(defaultProps.handleSaveOrNumber).toHaveBeenCalledWith('OR-2026-9999');
        expect(defaultProps.handleStatusUpdate).not.toHaveBeenCalled();
    });

    it('enforces release gate: blocks release when fee > 0 and O.R. is missing', () => {
        render(<ReviewDocumentModal {...defaultProps} />);

        const releaseBtn = screen.getByRole('button', { name: 'Release to Resident' });
        fireEvent.click(releaseBtn);

        expect(toast.error).toHaveBeenCalledWith('Official Receipt (O.R.) number is required before releasing a paid document.');
        expect(defaultProps.handleStatusUpdate).not.toHaveBeenCalled();
    });

    it('allows release when O.R. number is provided for paid document', () => {
        render(<ReviewDocumentModal {...defaultProps} />);

        const orInput = screen.getByPlaceholderText('e.g. OR-89104');
        fireEvent.change(orInput, { target: { value: 'OR-554433' } });

        const releaseBtn = screen.getByRole('button', { name: 'Release to Resident' });
        fireEvent.click(releaseBtn);

        expect(defaultProps.handleStatusUpdate).toHaveBeenCalledWith(
            'RELEASED',
            'OR-554433',
            '50.00',
        );
    });

    it('renders fee-exempt badge and allows release without O.R. number', () => {
        const exemptRequest: DocumentRequest = {
            ...baseRequest,
            document_type: 'First Time Job Seeker Certificate',
            fee_amount: '0.00',
            payment_status: 'NOT_REQUIRED',
            payment_reference: '',
            payment_proof_url: null,
        };

        render(<ReviewDocumentModal {...defaultProps} selectedRequest={exemptRequest} />);

        expect(screen.getByText(/Fee Exempt \(₱0\.00\) — RA 11261 \/ Indigency/)).toBeInTheDocument();
        const feeInput = screen.getByPlaceholderText('50.00');
        expect(feeInput).toBeDisabled();

        const releaseBtn = screen.getByRole('button', { name: 'Release to Resident' });
        fireEvent.click(releaseBtn);

        expect(toast.error).not.toHaveBeenCalled();
        expect(defaultProps.handleStatusUpdate).toHaveBeenCalledWith(
            'RELEASED',
            '',
            '0.00',
        );
    });

    it('allows staff to assess an ordinary request that starts with zero fee', () => {
        const unassessedRequest: DocumentRequest = {
            ...baseRequest,
            status: 'PROCESSING',
            fee_amount: '0.00',
            payment_status: 'NOT_REQUIRED',
            payment_method: '',
        };
        render(<ReviewDocumentModal {...defaultProps} selectedRequest={unassessedRequest} />);

        const feeInput = screen.getByPlaceholderText('50.00');
        expect(feeInput).toBeEnabled();
        expect(screen.queryByText(/Fee Exempt \(₱0\.00\)/)).not.toBeInTheDocument();
        fireEvent.change(feeInput, { target: { value: '50.00' } });
        fireEvent.click(screen.getByRole('button', { name: 'Mark Ready for Pickup' }));

        expect(defaultProps.handleStatusUpdate).toHaveBeenCalledWith(
            'READY_FOR_PICKUP',
            '',
            '50.00',
        );
    });

    it('renders cash instructions when payment method is CASH', () => {
        const cashRequest: DocumentRequest = {
            ...baseRequest,
            payment_method: 'CASH',
            payment_reference: '',
            payment_proof_url: null,
            payment_status: 'UNPAID',
        };

        render(<ReviewDocumentModal {...defaultProps} selectedRequest={cashRequest} />);

        expect(screen.getByText(/Cash payment will be settled in person at the Barangay Treasurer desk upon pickup\./)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /inspect receipt/i })).not.toBeInTheDocument();
    });

    it('handles verification and enforces mandatory note when rejecting payment', () => {
        render(<ReviewDocumentModal {...defaultProps} />);

        // Verify transfer
        const orInput = screen.getByPlaceholderText('e.g. OR-89104');
        fireEvent.change(orInput, { target: { value: 'OR-7788' } });

        const verifyBtn = screen.getByRole('button', { name: 'Verify Transfer' });
        fireEvent.click(verifyBtn);
        expect(defaultProps.handlePaymentReview).toHaveBeenCalledWith('VERIFIED', '', 'OR-7788');

        // Reject reference with note
        const rejectBtn = screen.getByRole('button', { name: 'Reject Reference' });
        expect(rejectBtn).toBeDisabled();

        const noteTextarea = screen.getByPlaceholderText(/Explain why the reference\/proof was rejected/);
        fireEvent.change(noteTextarea, { target: { value: 'Amount on screenshot shows 25 instead of 50' } });

        expect(rejectBtn).toBeEnabled();
        fireEvent.click(rejectBtn);
        expect(defaultProps.handlePaymentReview).toHaveBeenCalledWith(
            'REJECTED',
            'Amount on screenshot shows 25 instead of 50',
        );
    });

    it('renders awaiting assessment badge and blocks transition when fee is not assessed', () => {
        const unassessedRequest: DocumentRequest = {
            ...baseRequest,
            status: 'PROCESSING',
            fee_amount: 0,
            fee_assessment_status: 'AWAITING_ASSESSMENT',
            payment_status: 'NOT_REQUIRED',
            payment_method: '',
        };
        render(<ReviewDocumentModal {...defaultProps} selectedRequest={unassessedRequest} />);

        expect(screen.getByText('Awaiting Assessment')).toBeInTheDocument();

        // Clear fee input to 0
        const feeInput = screen.getByPlaceholderText('50.00');
        fireEvent.change(feeInput, { target: { value: '0' } });

        const readyBtn = screen.getByRole('button', { name: 'Mark Ready for Pickup' });
        fireEvent.click(readyBtn);

        expect(toast.error).toHaveBeenCalledWith('Document fee must be assessed or explicitly waived before marking ready for pickup.');
        expect(defaultProps.handleStatusUpdate).not.toHaveBeenCalled();
    });

    it('allows staff to waive fee with written justification', () => {
        const unassessedRequest: DocumentRequest = {
            ...baseRequest,
            status: 'PROCESSING',
            fee_amount: 0,
            fee_assessment_status: 'AWAITING_ASSESSMENT',
            payment_status: 'NOT_REQUIRED',
            payment_method: '',
        };
        render(<ReviewDocumentModal {...defaultProps} selectedRequest={unassessedRequest} />);

        const waiveCheckbox = screen.getByRole('checkbox', { name: /waive clearance fee for resident/i });
        fireEvent.click(waiveCheckbox);

        // Try to submit with empty justification
        const readyBtn = screen.getByRole('button', { name: 'Mark Ready for Pickup' });
        fireEvent.click(readyBtn);
        expect(toast.error).toHaveBeenCalledWith('A written justification is required to waive clearance fees.');
        expect(defaultProps.handleStatusUpdate).not.toHaveBeenCalled();

        // Provide written justification
        const reasonTextarea = screen.getByPlaceholderText(/State mandatory reason for fee waiver/i);
        fireEvent.change(reasonTextarea, { target: { value: 'Endorsed by Punong Barangay as indigent resident' } });

        fireEvent.click(readyBtn);
        expect(defaultProps.handleStatusUpdate).toHaveBeenCalledWith(
            'READY_FOR_PICKUP',
            '',
            '0.00',
            'Endorsed by Punong Barangay as indigent resident',
        );
    });

    it('renders staff waiver badge and displays existing waiver justification', () => {
        const waivedRequest: DocumentRequest = {
            ...baseRequest,
            status: 'READY_FOR_PICKUP',
            fee_amount: 0,
            fee_assessment_status: 'WAIVED',
            fee_assessed_by_name: 'Kagawad Juan',
            fee_assessed_at: '2026-10-13T10:00:00Z',
            fee_waiver_reason: 'Indigency referral from social welfare',
            payment_status: 'NOT_REQUIRED',
            payment_method: '',
        };
        render(<ReviewDocumentModal {...defaultProps} selectedRequest={waivedRequest} />);

        expect(screen.getByText('Staff Waiver')).toBeInTheDocument();
        expect(screen.getByText(/Assessment by:/)).toBeInTheDocument();
        expect(screen.getByText('Kagawad Juan')).toBeInTheDocument();
    });
});
