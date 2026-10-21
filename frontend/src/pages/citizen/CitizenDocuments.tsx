import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { axiosPrivate } from '../../api/axios';
import { getSafeApiErrorMessage } from '../../api/error-message';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { NewDocumentRequestModal } from '../../components/citizen-documents/NewDocumentRequestModal';
import { DOCUMENT_TYPES } from '../../components/citizen-documents/documentTypes';
import { DocumentRequestRow } from '../../components/citizen-documents/DocumentRequestRow';
import type { DocumentRequest, PaymentRecipient } from '../../components/citizen-documents/types';
import { useLanguage } from '../../context/language-context';
import {
    Plus,
    Loader2,
    FileCheck2,
} from 'lucide-react';

export const CitizenDocuments: React.FC = () => {
    const { t } = useLanguage();
    const [requests, setRequests] = useState<DocumentRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [downloadingId, setDownloadingId] = useState<number | null>(null);
    const [cancellingId, setCancellingId] = useState<number | null>(null);
    const [paymentReference, setPaymentReference] = useState<Record<number, string>>({});
    const [selectedRecipientId, setSelectedRecipientId] = useState<Record<number, string>>({});
    const [paymentRecipients, setPaymentRecipients] = useState<PaymentRecipient[]>([]);
    const [paymentRecipientsLoading, setPaymentRecipientsLoading] = useState(true);
    const [paymentRecipientsLoadError, setPaymentRecipientsLoadError] = useState(false);
    const [submittingPaymentId, setSubmittingPaymentId] = useState<number | null>(null);

    // Form State
    const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0]);
    const [purpose, setPurpose] = useState('');

    const fetchRequests = async () => {
        try {
            setLoading(true);
            const res = await axiosPrivate.get('/document-requests/');
            const data = res.data.results || res.data;
            setRequests(Array.isArray(data) ? data : []);
            setLoadError(false);
        } catch {
            setLoadError(true);
        } finally {
            setLoading(false);
        }
    };

    const fetchPaymentRecipients = async () => {
        setPaymentRecipientsLoading(true);
        try {
            const response = await axiosPrivate.get('/payment-recipients/');
            const data = response.data.results || response.data;
            if (!Array.isArray(data)) {
                throw new Error('Invalid payment recipient response');
            }
            setPaymentRecipients(data);
            setPaymentRecipientsLoadError(false);
        } catch {
            setPaymentRecipientsLoadError(true);
        } finally {
            setPaymentRecipientsLoading(false);
        }
    };

    useEffect(() => {
        fetchRequests();
        void fetchPaymentRecipients();
    }, []);

    const handleCreateRequest = async (e: React.SubmitEvent<HTMLElement>) => {
        e.preventDefault();
        if (!purpose.trim()) {
            toast.error(t('Please specify a valid purpose for this certificate.'));
            return;
        }

        try {
            setSubmitting(true);
            await axiosPrivate.post('/document-requests/', {
                document_type: documentType,
                purpose: purpose.trim(),
            });
            toast.success(t('Document request filed successfully!'));
            setIsModalOpen(false);
            setPurpose('');
            fetchRequests();
        } catch (err) {
            toast.error(getSafeApiErrorMessage(
                err,
                t("We couldn't submit your document request. Check your connection and try again."),
            ));
        } finally {
            setSubmitting(false);
        }
    };

    const handleCancelRequest = async (id: number) => {
        if (!window.confirm(t('Are you sure you want to cancel this pending clearance application?'))) {
            return;
        }

        try {
            setCancellingId(id);
            await axiosPrivate.delete(`/document-requests/${id}/`);
            setRequests((prev) => prev.filter((r) => r.id !== id));
            toast.success(t('Document request cancelled.'));
        } catch (err) {
            toast.error(getSafeApiErrorMessage(
                err,
                t("We couldn't cancel your request. Check your connection and try again."),
            ));
        } finally {
            setCancellingId(null);
        }
    };

    const handleDownloadPdf = async (id: number, docType: string) => {
        try {
            setDownloadingId(id);
            const res = await axiosPrivate.get(`/document-requests/${id}/generate-pdf/`, {
                responseType: 'blob',
            });
            const blob = new Blob([res.data], { type: 'application/pdf' });
            const downloadUrl = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = `${docType.replace(/\s+/g, '_')}_${id}.pdf`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(downloadUrl);
            toast.success(t('Certificate downloaded.'));
        } catch{
            toast.error(t('Could not generate PDF. Please contact the barangay hall.'));
        } finally {
            setDownloadingId(null);
        }
    };

    const handleSubmitPaymentReference = async (id: number, formData: FormData) => {
        setSubmittingPaymentId(id);
        try {
            const response = await axiosPrivate.post(
                `/document-requests/${id}/payment-reference/`,
                formData,
                {
                    headers: { 'Content-Type': 'multipart/form-data' },
                },
            );
            setRequests((current) => current.map((request) =>
                request.id === id ? { ...request, ...response.data } : request,
            ));
            setPaymentReference((current) => ({ ...current, [id]: '' }));
            toast.success(t('Transfer reference and receipt sent to barangay staff for manual verification.'));
        } catch (err: any) {
            toast.error(err.response?.data?.detail || t('Could not submit the payment reference.'));
        } finally {
            setSubmittingPaymentId(null);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header Banner */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                        {t('Barangay Clearances & Certificates')}
                    </h1>
                    <p className="text-sm text-slate-500 mt-1">
                        {t('Request official barangay documents, monitor live processing status, and download authenticated certificates.')}
                    </p>
                </div>
                <button
                    onClick={() => setIsModalOpen(true)}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-primary-foreground text-sm font-semibold shadow-xs transition-all cursor-pointer shrink-0"
                >
                    <Plus className="w-4 h-4" />
                    <span>{t('Request New Clearance')}</span>
                </button>
            </div>

            {/* Requests List */}
            {loading ? (
                <div className="bg-white rounded-2xl p-12 border border-slate-200 flex flex-col items-center justify-center text-slate-400">
                    <Loader2 className="w-8 h-8 animate-spin text-primary-text mb-2" />
                    <p className="text-sm">{t('Retrieving your certificate records...')}</p>
                </div>
            ) : loadError ? (
                <InlineErrorState
                    message={t("We couldn't load your document requests.")}
                    onRetry={() => void fetchRequests()}
                    retrying={loading}
                />
            ) : requests.length === 0 ? (
                <div className="bg-white rounded-2xl p-12 border border-slate-200 text-center flex flex-col items-center justify-center">
                    <div className="w-14 h-14 rounded-2xl bg-sky-50 text-primary-text flex items-center justify-center mb-3">
                        <FileCheck2 className="w-7 h-7" />
                    </div>
                    <h3 className="text-base font-bold text-slate-900">{t('No active document requests')}</h3>
                    <p className="text-sm text-slate-500 max-w-sm mt-1">
                        {t("You haven't filed any clearance applications yet. Click the button below to submit a new request.")}
                    </p>
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="mt-4 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-hover transition-all cursor-pointer"
                    >
                        {t('Request Clearance')}
                    </button>
                </div>
            ) : (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-slate-700">
                            <thead className="bg-[#F8FAFD] border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
                                <tr>
                                    <th className="py-4 px-6">{t('Document Type')}</th>
                                    <th className="py-4 px-6">{t('Declared Purpose')}</th>
                                    <th className="py-4 px-6">{t('Date Requested')}</th>
                                    <th className="py-4 px-6">{t('Current Status')}</th>
                                    <th className="py-4 px-6 text-right">{t('Actions')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {requests.map((request) => (
                                    <DocumentRequestRow
                                        key={request.id}
                                        request={request}
                                        recipients={paymentRecipients}
                                        recipientsLoading={paymentRecipientsLoading}
                                        recipientsLoadError={paymentRecipientsLoadError}
                                        onRetryRecipients={() => void fetchPaymentRecipients()}
                                        selectedRecipientId={selectedRecipientId[request.id] || ''}
                                        paymentReference={paymentReference[request.id] ?? ''}
                                        submittingPayment={submittingPaymentId === request.id}
                                        downloading={downloadingId === request.id}
                                        cancelling={cancellingId === request.id}
                                        onRecipientChange={(value) =>
                                            setSelectedRecipientId((current) => ({
                                                ...current,
                                                [request.id]: value,
                                            }))
                                        }
                                        onPaymentReferenceChange={(value) =>
                                            setPaymentReference((current) => ({
                                                ...current,
                                                [request.id]: value,
                                            }))
                                        }
                                        onSubmitPaymentReference={(formData) => handleSubmitPaymentReference(request.id, formData)}
                                        onDownloadPdf={() => handleDownloadPdf(request.id, request.document_type)}
                                        onCancel={() => handleCancelRequest(request.id)}
                                    />
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {isModalOpen && (
                <NewDocumentRequestModal
                    documentType={documentType}
                    purpose={purpose}
                    submitting={submitting}
                    onDocumentTypeChange={setDocumentType}
                    onPurposeChange={setPurpose}
                    onClose={() => setIsModalOpen(false)}
                    onSubmit={handleCreateRequest}
                />
            )}
        </div>
    );
};
