import toast from 'react-hot-toast';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { axiosPrivate } from '../../api/axios';
import { getSafeApiErrorMessage } from '../../api/error-message';
import { DocumentTable } from '../../components/documents/DocumentTable';
import { ReviewDocumentModal } from '../../components/documents/ReviewDocumentModal';
import { WalkinRequestModal } from '../../components/documents/WalkinRequestModal';
import { DocumentCatalogManagerModal } from '../../components/documents/DocumentCatalogManagerModal';
import { type DocumentServiceOffering } from '../../components/documents/documentCatalog';
import { isFeeExemptDocumentType } from '../../utils/documentFees';
import { useLanguage } from '../../context/language-context';

export interface DocumentRequest {
    id: number;
    offering_id?: number | null;
    requirements_snapshot?: string[];
    published_fee_amount_snapshot?: string | null;
    offering_details_snapshot?: string;
    request_id?: number;
    requester_name?: string;
    purok?: string;
    is_walkin?: boolean;
    walkin_name?: string;
    walkin_purok?: string;
    document_type: string;
    purpose?: string;
    urgency_tag?: 'REGULAR' | 'URGENT';
    status: string;
    admin_notes?: string;
    or_number?: string;
    fee_amount?: number | string;
    fee_assessment_status?: 'AWAITING_ASSESSMENT' | 'ASSESSED' | 'WAIVED' | 'STATUTORY_EXEMPT' | string;
    fee_assessed_by_name?: string | null;
    fee_assessed_at?: string | null;
    fee_waiver_reason?: string;
    payment_method?: string;
    payment_recipient?: number | null;
    payment_recipient_name_snapshot?: string | null;
    payment_recipient_identifier_snapshot?: string | null;
    payment_instructions_snapshot?: string | null;
    payment_reference?: string;
    payment_status?: string;
    payment_review_note?: string;
    payment_transacted_at?: string | null;
    payment_proof_url?: string | null;
    created_at: string;
}

const TableSkeleton = () => (
    <div className="space-y-6 animate-pulse">
        <div className="flex justify-between items-center">
            <div className="h-8 w-48 bg-slate-200 rounded"></div>
            <div className="h-10 w-32 bg-slate-200 rounded-md"></div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 h-12 border-b border-slate-200 w-full"></div>
            {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex h-16 border-b border-slate-100 items-center px-6 gap-4">
                    <div className="h-4 w-12 bg-slate-200 rounded"></div>
                    <div className="h-4 w-48 bg-slate-200 rounded"></div>
                    <div className="h-4 w-32 bg-slate-200 rounded"></div>
                    <div className="h-4 w-24 bg-slate-200 rounded"></div>
                    <div className="h-6 w-20 bg-slate-200 rounded-full"></div>
                </div>
            ))}
        </div>
    </div>
);

export const DocumentRequests: React.FC = () => {
    const { t } = useLanguage();
    const [requests, setRequests] = useState<DocumentRequest[]>([]);
    const [offerings, setOfferings] = useState<DocumentServiceOffering[]>([]);
    const [offeringsLoadError, setOfferingsLoadError] = useState(false);
    const [offeringsLoaded, setOfferingsLoaded] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [retrying, setRetrying] = useState(false);
    const requestsFetchInProgress = useRef(false);

    const [selectedRequest, setSelectedRequest] = useState<DocumentRequest | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isUpdating, setIsUpdating] = useState(false);
    
    // Walk-in Dialog State
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [walkinName, setWalkinName] = useState('');
    const [walkinPurok, setWalkinPurok] = useState('');
    const [newDocType, setNewDocType] = useState('');
    const [selectedOfferingId, setSelectedOfferingId] = useState<number | null>(null);
    const [newPurpose, setNewPurpose] = useState('');
    const [isCatalogModalOpen, setIsCatalogModalOpen] = useState(false);

    const fetchRequests = useCallback(async (isRetry = false) => {
        if (requestsFetchInProgress.current) return;
        requestsFetchInProgress.current = true;
        if (isRetry) setRetrying(true);

        try {
            const response = await axiosPrivate.get('/document-requests/');
            setRequests(response.data.results || response.data);
            setError('');
        } catch (err) {
            setError('Failed to load document requests.');
            console.error(err);
        } finally {
            requestsFetchInProgress.current = false;
            setLoading(false);
            setRetrying(false);
        }
    }, []);

    const fetchOfferings = useCallback(async () => {
        try {
            const response = await axiosPrivate.get('/document-catalog/');
            const data = response.data.results || response.data;
            setOfferings(Array.isArray(data) ? data : []);
            setOfferingsLoadError(false);
        } catch (err) {
            setOfferingsLoadError(true);
            toast.error(getSafeApiErrorMessage(
                err,
                "We couldn't load your Barangay's document service catalog.",
            ));
        } finally {
            setOfferingsLoaded(true);
        }
    }, []);

    useEffect(() => {
        void fetchRequests();
        const refreshWhenVisible = () => {
            if (document.visibilityState === 'visible') {
                void fetchRequests();
            }
        };
        const intervalId = window.setInterval(refreshWhenVisible, 3000);
        document.addEventListener('visibilitychange', refreshWhenVisible);
        window.addEventListener('focus', refreshWhenVisible);

        return () => {
            window.clearInterval(intervalId);
            document.removeEventListener('visibilitychange', refreshWhenVisible);
            window.removeEventListener('focus', refreshWhenVisible);
        };
    }, [fetchRequests]);

    const getStatusBadge = (status: string) => {
        switch (status.toLowerCase()) {
            case 'pending': 
                return 'bg-amber-100 text-amber-800 border-amber-200';
            case 'processing': 
                return 'bg-sky-100 text-sky-800 border-sky-200';
            case 'ready_for_pickup': 
                return 'bg-purple-100 text-purple-800 border-purple-200';
            case 'released': 
                return 'bg-emerald-100 text-emerald-800 border-emerald-200';
            case 'rejected': 
                return 'bg-rose-100 text-rose-800 border-rose-200';
            default: 
                return 'bg-slate-100 text-slate-800 border-slate-200';
        }
    };

    const openModal = (request: DocumentRequest) => {
        setSelectedRequest(request);
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setSelectedRequest(null);
    };

    const handleStatusUpdate = async (
        newStatus: string,
        updatedOr?: string,
        updatedFee?: string,
        paymentMethod?: string,
        feeWaiverReason?: string,
    ) => {
        if (!selectedRequest) return;
        setIsUpdating(true);

        try {
            const payload: Record<string, any> = {
                status: newStatus,
                or_number: updatedOr,
                fee_amount: isFeeExemptDocumentType(selectedRequest.document_type) ? '0.00' : updatedFee,
                payment_method: paymentMethod,
            };
            if (feeWaiverReason !== undefined) {
                payload.fee_waiver_reason = feeWaiverReason;
            }

            const response = await axiosPrivate.patch(`/document-requests/${selectedRequest.id}/validate/`, payload);

            setRequests(prev => prev.map(req =>
                req.id === selectedRequest.id ? { ...req, ...response.data } : req
            ));
            toast.success(`Request marked as ${newStatus.replace(/_/g, ' ')}`);
            closeModal();
        } catch (err) {
            console.error("Failed to update status", err);
            toast.error('Failed to update status. Please check permissions or try again.');
        } finally {
            setIsUpdating(false);
        }
    };

    const handlePaymentReview = async (paymentStatus: 'VERIFIED' | 'REJECTED', note: string, orNumber?: string) => {
        if (!selectedRequest) return;
        setIsUpdating(true);
        try {
            const payload: { status: 'VERIFIED' | 'REJECTED'; note: string; or_number?: string } = {
                status: paymentStatus,
                note,
            };
            if (orNumber?.trim()) {
                payload.or_number = orNumber.trim();
            }
            const response = await axiosPrivate.patch(
                `/document-requests/${selectedRequest.id}/payment-review/`,
                payload,
            );
            setRequests((current) => current.map((request) =>
                request.id === selectedRequest.id ? { ...request, ...response.data } : request,
            ));
            setSelectedRequest((current) => current ? { ...current, ...response.data } : current);
            toast.success(paymentStatus === 'VERIFIED' ? 'Electronic transfer verified.' : 'Transfer reference rejected with a reason.');
        } catch (err: any) {
            toast.error(err.response?.data?.note?.[0] || err.response?.data?.detail || 'Could not review this electronic payment.');
        } finally {
            setIsUpdating(false);
        }
    };

    const handleSaveOrNumber = async (orNumber: string) => {
        if (!selectedRequest) return;
        setIsUpdating(true);
        try {
            const response = await axiosPrivate.patch(`/document-requests/${selectedRequest.id}/validate/`, {
                status: selectedRequest.status,
                or_number: orNumber.trim(),
                fee_amount: isFeeExemptDocumentType(selectedRequest.document_type) ? '0.00' : selectedRequest.fee_amount,
                payment_method: selectedRequest.payment_method,
            });
            setRequests((prev) => prev.map((req) =>
                req.id === selectedRequest.id ? { ...req, ...response.data } : req,
            ));
            setSelectedRequest((prev) => prev ? { ...prev, ...response.data } : prev);
            toast.success('Official Receipt (O.R.) number saved.');
        } catch (err: any) {
            console.error('Failed to save O.R. number', err);
            toast.error(err?.response?.data?.or_number?.[0] || 'Failed to save O.R. number.');
        } finally {
            setIsUpdating(false);
        }
    };

    const handleDownloadPDF = async () => {
        if (!selectedRequest) return;
        try {
            const response = await axiosPrivate.get(`/document-requests/${selectedRequest.id}/generate-pdf/`, {
                responseType: 'blob'
            });

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${selectedRequest.document_type.replace(/ /g, '_')}_${selectedRequest.id}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            toast.success('Clearance certificate downloaded.');
        } catch (error) {
            console.error("Failed to download PDF", error);
            toast.error('Failed to generate PDF. Make sure the document is approved or released.');
        }
    };

    const handleDeleteRequest = async (id: number) => {
        const confirmed = window.confirm('Are you sure you want to delete this clearance request? This action cannot be undone.');
        if (!confirmed) return;

        try {
            await axiosPrivate.delete(`/document-requests/${id}/`);
            setRequests(prev => prev.filter(req => req.id !== id));
            toast.success('Clearance request deleted successfully.');
        } catch (err) {
            toast.error(getSafeApiErrorMessage(
                err,
                "We couldn't delete this clearance request. Check your connection and try again.",
            ));
        }
    };

    const handleCreateWalkinRequest = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        if (!walkinName.trim()) {
            toast.error("Please enter the resident's full name.");
            return;
        }

        const selectedOffering = offerings.find((offering) => offering.id === selectedOfferingId && offering.is_active);
        const requestedDocumentType = selectedOffering?.document_type ?? newDocType.trim();
        if (!requestedDocumentType || requestedDocumentType.length > 100) {
            toast.error('Enter a document name between 1 and 100 characters.');
            return;
        }

        setIsSubmitting(true);
        try {
            await axiosPrivate.post('/document-requests/', {
                walkin_name: walkinName.trim(),
                walkin_purok: walkinPurok.trim(),
                document_type: requestedDocumentType,
                ...(selectedOffering ? { offering_id: selectedOffering.id } : {}),
                purpose: newPurpose.trim(),
            });

            toast.success('Walk-in request submitted for review.');
            await fetchRequests();

            setIsCreateModalOpen(false);
            setWalkinName('');
            setWalkinPurok('');
            setNewPurpose('');
            setNewDocType('');
            setSelectedOfferingId(null);
        } catch (err) {
            toast.error(getSafeApiErrorMessage(
                err,
                "We couldn't submit this walk-in request. Check your connection and try again.",
            ));
        } finally {
            setIsSubmitting(false);
        }
    };

    const openWalkinRequest = () => {
        setSelectedOfferingId(offerings.find((offering) => offering.is_active)?.id ?? null);
        setIsCreateModalOpen(true);
    };

    const openCatalogManager = async () => {
        await fetchOfferings();
        setIsCatalogModalOpen(true);
    };

    if (loading) return <div className="p-4 md:p-8"><TableSkeleton /></div>;

    return (
        <div className="space-y-6 relative">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-slate-900 tracking-tight">{t('Clearance Desk & Document Requests')}</h2>
                    <p className="text-sm text-slate-500 mt-1">{t('Manage resident document requests and set your Barangay requirements, published fees, and details.')}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                    <button
                        type="button"
                        onClick={openCatalogManager}
                        className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 shadow-sm transition-all hover:bg-slate-50"
                    >
                        {t('Manage document services')}
                    </button>
                    <button
                        onClick={openWalkinRequest}
                        className="bg-primary hover:bg-primary-hover active:bg-primary-hover text-primary-foreground px-5 py-2.5 rounded-xl text-sm font-bold shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer"
                    >
                        <span>+</span> {t('Request Walk-in')}
                    </button>
                </div>
            </div>

            {offeringsLoaded && offeringsLoadError ? (
                <div role="alert" className="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900 sm:flex-row sm:items-center sm:justify-between">
                    <span>{t("We couldn't load your document service catalog. Residents may not see current requirements until it is available.")}</span>
                    <button type="button" onClick={() => void fetchOfferings()} className="shrink-0 rounded-lg border border-rose-300 bg-white px-3 py-2 font-semibold">{t('Retry catalog')}</button>
                </div>
            ) : offeringsLoaded && !offerings.some((offering) => offering.is_active) ? (
                <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                    {t('No active document services are published. Add each document your Barangay offers, then save it to show its requirements and fee to residents.')}
                </div>
            ) : null}

            <DocumentTable
                requests={requests}
                openModal={openModal}
                getStatusBadge={getStatusBadge}
                onDelete={handleDeleteRequest}
                loadError={error ? {
                    message: "We couldn't load document requests.",
                    onRetry: () => void fetchRequests(true),
                    retrying,
                } : undefined}
            />

            {isModalOpen && selectedRequest && (
                <ReviewDocumentModal
                    selectedRequest={selectedRequest}
                    closeModal={closeModal}
                    getStatusBadge={getStatusBadge}
                    handleStatusUpdate={handleStatusUpdate}
                    handlePaymentReview={handlePaymentReview}
                    handleSaveOrNumber={handleSaveOrNumber}
                    isUpdating={isUpdating}
                    handleDownloadPDF={handleDownloadPDF}
                />
            )}

            {/* Log Walk-in Clearance Modal */}
            {isCreateModalOpen && (
                <WalkinRequestModal
                    onClose={() => setIsCreateModalOpen(false)}
                    onSubmit={handleCreateWalkinRequest}
                    walkinName={walkinName}
                    setWalkinName={setWalkinName}
                    walkinPurok={walkinPurok}
                    setWalkinPurok={setWalkinPurok}
                    offerings={offerings.filter((offering) => offering.is_active)}
                    selectedOfferingId={selectedOfferingId}
                    setSelectedOfferingId={setSelectedOfferingId}
                    newDocType={newDocType}
                    setNewDocType={setNewDocType}
                    newPurpose={newPurpose}
                    setNewPurpose={setNewPurpose}
                    isSubmitting={isSubmitting}
                />
            )}
            {isCatalogModalOpen && (
                <DocumentCatalogManagerModal
                    offerings={offerings}
                    onClose={() => setIsCatalogModalOpen(false)}
                    onSaved={async () => { await fetchOfferings(); }}
                />
            )}
        </div>
    );
};
