import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { DocumentRequest } from '../../pages/services/DocumentRequests';
import { NewDocumentRequestModal } from '../citizen-documents/NewDocumentRequestModal';
import { ReviewDocumentModal } from '../documents/ReviewDocumentModal';
import { WalkinRequestModal } from '../documents/WalkinRequestModal';
import { BroadcastAnnouncementModal } from '../announcements/BroadcastAnnouncementModal';
import { ScheduleActivityModal } from '../activities/ScheduleActivityModal';
import { AddHotlineModal } from '../hotlines/AddHotlineModal';
import { DigitalQueueTicketModal } from '../queue/DigitalQueueTicketModal';
import { NewTicketModal } from '../queue/NewTicketModal';

describe('accessible modal names', () => {
    it('names the manual queue entry dialog', () => {
        render(
            <NewTicketModal
                handleCloseManualModal={vi.fn()}
                handleCreateManualTicket={vi.fn()}
                searchResident=""
                setSearchResident={vi.fn()}
                serviceRequired=""
                setServiceRequired={vi.fn()}
                canManagePriority={false}
                priorityStatus="regular"
                setPriorityStatus={vi.fn()}
                priorityReason=""
                setPriorityReason={vi.fn()}
                notes=""
                setNotes={vi.fn()}
                isSubmittingNew={false}
            />,
        );

        expect(screen.getByRole('dialog', { name: 'Manual Queue Entry' })).toBeInTheDocument();
    });

    it('names the clearance request dialog', () => {
        render(
            <NewDocumentRequestModal
                documentType="Barangay Clearance"
                purpose="Employment"
                otherDocumentType=""
                submitting={false}
                onOtherDocumentTypeChange={vi.fn()}
                onDocumentTypeChange={vi.fn()}
                onPurposeChange={vi.fn()}
                onClose={vi.fn()}
                onSubmit={vi.fn()}
            />,
        );

        expect(screen.getByRole('dialog', { name: 'Request a document' })).toBeInTheDocument();
    });

    it('names the document review dialog', () => {
        const request: DocumentRequest = {
            id: 42,
            document_type: 'Barangay Clearance',
            status: 'PENDING',
            created_at: '2026-10-10T00:00:00Z',
        };

        render(
            <ReviewDocumentModal
                selectedRequest={request}
                closeModal={vi.fn()}
                getStatusBadge={() => ''}
                handleStatusUpdate={vi.fn()}
                handlePaymentReview={vi.fn()}
                isUpdating={false}
                handleDownloadPDF={vi.fn()}
            />,
        );

        expect(screen.getByRole('dialog', { name: 'Request #42' })).toBeInTheDocument();
    });

    it('names the walk-in request dialog', () => {
        render(
            <WalkinRequestModal
                onClose={vi.fn()}
                onSubmit={vi.fn()}
                walkinName="Juan Dela Cruz"
                setWalkinName={vi.fn()}
                walkinPurok="Purok 1"
                setWalkinPurok={vi.fn()}
                newDocType="Barangay Clearance"
                setNewDocType={vi.fn()}
                newPurpose="Employment"
                setNewPurpose={vi.fn()}
                isSubmitting={false}
            />,
        );

        expect(screen.getByRole('dialog', { name: 'Create Walk-in Request' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Close walk-in request dialog' })).toBeInTheDocument();
        expect(screen.getByLabelText('Resident Full Name *')).toBeInTheDocument();
    });

    it('names the broadcast announcement dialog', () => {
        render(
            <BroadcastAnnouncementModal
                onClose={vi.fn()}
                onSubmit={vi.fn()}
                title="Community Assembly"
                setTitle={vi.fn()}
                content="Notice of general assembly"
                setContent={vi.fn()}
                isPinned={false}
                setIsPinned={vi.fn()}
                imagePreview={null}
                onImageChange={vi.fn()}
                onRemoveImage={vi.fn()}
                isSubmitting={false}
            />,
        );

        expect(screen.getByRole('dialog', { name: 'Broadcast Announcement' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Close broadcast announcement dialog' })).toBeInTheDocument();
        expect(screen.getByLabelText('Headline')).toBeInTheDocument();
    });

    it('names the schedule activity dialog', () => {
        render(
            <ScheduleActivityModal
                onClose={vi.fn()}
                onSubmit={vi.fn()}
                title="Barangay Clean-up"
                setTitle={vi.fn()}
                location="Covered Court"
                setLocation={vi.fn()}
                eventDate="2026-10-15T09:00"
                setEventDate={vi.fn()}
                description="Annual clean-up drive"
                setDescription={vi.fn()}
                isSubmitting={false}
            />,
        );

        expect(screen.getByRole('dialog', { name: 'Schedule Activity' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Close schedule activity dialog' })).toBeInTheDocument();
        expect(screen.getByLabelText('Event Title')).toBeInTheDocument();
    });

    it('names the emergency hotline dialog', () => {
        render(
            <AddHotlineModal
                onClose={vi.fn()}
                onSubmit={vi.fn()}
                form={{ name: 'PNP Station', number: '117', category: 'POLICE' }}
                setForm={vi.fn()}
                categories={['POLICE', 'FIRE', 'MEDICAL', 'BARANGAY', 'OTHER']}
                isSubmitting={false}
            />,
        );

        expect(screen.getByRole('dialog', { name: 'Add Emergency Hotline' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Close add emergency hotline dialog' })).toBeInTheDocument();
        expect(screen.getByLabelText('Name')).toBeInTheDocument();
    });

    it('names the digital queue ticket dialog', () => {
        render(
            <DigitalQueueTicketModal
                onClose={vi.fn()}
                onSubmit={vi.fn()}
                serviceType="Document Processing & Clearances"
                setServiceType={vi.fn()}
                serviceTypes={['Document Processing & Clearances', 'Barangay ID Application']}
                submitting={false}
            />,
        );

        expect(screen.getByRole('dialog', { name: 'Generate Digital Queue Ticket' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Close queue ticket form' })).toBeInTheDocument();
        expect(screen.getByLabelText('Select Service')).toBeInTheDocument();
    });
});
