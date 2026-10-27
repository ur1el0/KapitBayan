import React, { useState } from 'react';
import {
    AlertCircle,
    CheckCircle2,
    Clock,
    Download,
    FileText,
    ImageIcon,
    Loader2,
    Trash2,
    Ticket,
    X,
} from 'lucide-react';
import { PaymentReferenceForm } from './PaymentReferenceForm';
import type { DocumentRequest, PaymentRecipient } from './types';
import { usePrivateMediaUrl } from '../../hooks/usePrivateMediaUrl';
import { isFeeExemptDocumentType } from '../../utils/documentFees';
import { useLanguage } from '../../context/language-context';
import { formatPublishedFee } from '../documents/documentCatalog';

interface DocumentRequestRowProps {
    request: DocumentRequest;
    recipients: PaymentRecipient[];
    recipientsLoading: boolean;
    recipientsLoadError: boolean;
    onRetryRecipients: () => void;
    choosingPayment?: boolean;
    paymentReference?: string;
    submittingPayment: boolean;
    downloading: boolean;
    cancelling: boolean;
    requestingCounterTicket: boolean;
    onChoosePaymentMethod?: (choice: string) => void;
    onPaymentReferenceChange?: (value: string) => void;
    onSubmitPaymentReference: (formData: FormData) => void;
    onDownloadPdf: () => void;
    onCancel: () => void;
    onGetCounterTicket: () => void;
}

const RequestStatusBadge: React.FC<{ status: string }> = ({ status }) => {
    const { t } = useLanguage();
    switch (status.toUpperCase()) {
        case 'PENDING':
            return (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    <Clock className="w-3.5 h-3.5" /> {t('Pending Review')}
                </span>
            );
        case 'PROCESSING':
            return (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> {t('Processing')}
                </span>
            );
        case 'READY_FOR_PICKUP':
        case 'RELEASED':
            return (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5" /> {t('Ready / Released')}
                </span>
            );
        case 'REJECTED':
            return (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                    <AlertCircle className="w-3.5 h-3.5" /> {t('Rejected')}
                </span>
            );
        default:
            return (
                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                    {status}
                </span>
            );
    }
};

import { createPortal } from 'react-dom';

interface ProofPreviewModalProps {
    isOpen: boolean;
    proofUrl: string | null;
    reference?: string;
    onClose: () => void;
}

const ProofPreviewModal: React.FC<ProofPreviewModalProps> = ({
    isOpen,
    proofUrl,
    reference,
    onClose,
}) => {
    const { t } = useLanguage();
    const { url, isLoading, hasError } = usePrivateMediaUrl(isOpen ? proofUrl : null);

    if (!isOpen || typeof document === 'undefined') return null;

    return createPortal(
        <div
            role="dialog"
            aria-modal="true"
            aria-label={t('Payment receipt preview')}
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4"
            onClick={onClose}
        >
            <div
                className="relative max-w-lg w-full bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-200"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 bg-slate-50">
                    <div className="flex items-center gap-2">
                        <ImageIcon className="w-4 h-4 text-slate-700" />
                        <h3 className="text-xs font-bold text-slate-900">
                            {t('Uploaded Payment Receipt')} {reference ? `(${reference})` : ''}
                        </h3>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label={t('Close receipt preview')}
                        className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
                <div className="p-4 flex flex-col items-center justify-center min-h-[240px] max-h-[70vh] overflow-auto bg-slate-950/5">
                    {isLoading ? (
                        <div className="flex flex-col items-center gap-2 text-slate-500 py-10">
                            <Loader2 className="w-6 h-6 animate-spin text-primary-text" />
                            <span className="text-xs">{t('Loading receipt image…')}</span>
                        </div>
                    ) : hasError || !url ? (
                        <div className="flex flex-col items-center gap-2 text-rose-600 py-10">
                            <AlertCircle className="w-6 h-6" />
                            <span className="text-xs font-medium">{t('Could not load payment proof image.')}</span>
                        </div>
                    ) : (
                        <img
                            src={url}
                            alt={t('Payment receipt proof')}
                            className="max-h-[60vh] w-auto max-w-full rounded-lg object-contain shadow-xs"
                        />
                    )}
                </div>
                <div className="px-5 py-3 border-t border-slate-100 bg-slate-50 text-right">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-3.5 py-1.5 rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                    >
                        {t('Close')}
                    </button>
                </div>
            </div>
        </div>,
        document.body,
    );
};

export const DocumentRequestRow: React.FC<DocumentRequestRowProps> = ({
    request,
    recipients,
    recipientsLoading,
    recipientsLoadError,
    onRetryRecipients,
    choosingPayment = false,
    paymentReference,
    submittingPayment,
    downloading,
    cancelling,
    requestingCounterTicket,
    onChoosePaymentMethod,
    onPaymentReferenceChange,
    onSubmitPaymentReference,
    onDownloadPdf,
    onCancel,
    onGetCounterTicket,
}) => {
    const { t } = useLanguage();
    const [isPreviewOpen, setIsPreviewOpen] = useState(false);
    const [isRetrying, setIsRetrying] = useState(false);

    const isAvailableForDownload = ['READY_FOR_PICKUP', 'RELEASED'].includes(
        request.status.toUpperCase(),
    );

    const isStatutoryFeeExempt = isFeeExemptDocumentType(request.document_type) || request.fee_assessment_status === 'STATUTORY_EXEMPT';
    const isStaffWaived = request.fee_assessment_status === 'WAIVED';
    const isPaymentNotRequired = isStatutoryFeeExempt || isStaffWaived || Number(request.fee_amount ?? 0) <= 0;

    const isCash = request.payment_method === 'CASH';
    const canChoosePayment =
        request.status.toUpperCase() === 'READY_FOR_PICKUP' &&
        !isPaymentNotRequired &&
        (!request.payment_status || ['UNPAID', 'REJECTED'].includes(request.payment_status));
    const selectedPaymentChoice = isCash
        ? 'CASH'
        : request.payment_recipient
            ? `RECIPIENT:${request.payment_recipient}`
            : '';
    const activeSelectedRecipient = recipients.find(
        (recipient) => recipient.id === request.payment_recipient,
    );
    const isElectronicPayment = Boolean(
        !isCash && request.payment_recipient && activeSelectedRecipient,
    );
    const hasOfferingSnapshot = Boolean(
        request.offering_id
        || request.requirements_snapshot?.length
        || (request.published_fee_amount_snapshot !== null && request.published_fee_amount_snapshot !== undefined)
        || request.offering_details_snapshot,
    );

    const formatDateTime = (isoString?: string | null) => {
        if (!isoString) return '';
        try {
            const d = new Date(isoString);
            if (isNaN(d.getTime())) return isoString;
            return d.toLocaleString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
            });
        } catch {
            return isoString;
        }
    };

    return (
        <>
            <tr className="hover:bg-slate-50/70 transition-colors">
                <td className="py-4 px-6 font-semibold text-slate-900 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-primary-text" />
                    <div>
                        <div>{t(request.document_type)}</div>
                        {hasOfferingSnapshot && (
                            <div className="mt-1 max-w-xs space-y-1 text-left text-[11px] font-normal text-slate-600">
                                <p className="font-semibold text-slate-700">
                                    {t('Published fee')}: {t(formatPublishedFee(request.published_fee_amount_snapshot))}
                                </p>
                                {request.requirements_snapshot?.length ? (
                                    <p>
                                        {t('Requirements')}: {request.requirements_snapshot.map(t).join(' · ')}
                                    </p>
                                ) : (
                                    <p>{t('No requirements were listed.')}</p>
                                )}
                                {request.offering_details_snapshot && (
                                    <p>{t(request.offering_details_snapshot)}</p>
                                )}
                            </div>
                        )}
                    </div>
                </td>
                <td className="py-4 px-6 text-slate-600">
                    {request.purpose || '—'}
                </td>
                <td className="py-4 px-6 text-slate-500 text-xs">
                    {new Date(request.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                    })}
                </td>
                <td className="py-4 px-6 space-y-2">
                    <RequestStatusBadge status={request.status} />

                    {/* Fee-Exempt Badge (REV-07) */}
                    {isStatutoryFeeExempt && (
                        <div>
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                <span>{t('Statutory Fee Exemption — No Payment Required (RA 11261 / Indigency)')}</span>
                            </span>
                        </div>
                    )}

                    {/* Staff-Approved Waiver Banner */}
                    {isStaffWaived && (
                        <div className="p-2.5 rounded-xl border border-emerald-200 bg-emerald-50 text-xs text-emerald-900 space-y-1">
                            <p className="font-bold flex items-center gap-1.5 text-emerald-800">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                                <span>{t('Fee Waived (₱0.00) — Staff Approved')}</span>
                            </p>
                            {request.fee_waiver_reason && (
                                <p className="text-emerald-800">
                                    <span className="font-semibold">{t('Reason:')}</span> {request.fee_waiver_reason}
                                </p>
                            )}
                        </div>
                    )}

                    {/* Processing State Guidance Banner */}
                    {!isStatutoryFeeExempt && !isStaffWaived && request.status.toUpperCase() === 'PROCESSING' && (
                        <div className="p-3 rounded-xl border border-blue-200 bg-blue-50/70 text-xs text-blue-900 space-y-1">
                            <p className="font-semibold flex items-center gap-1.5">
                                <Clock className="w-4 h-4 text-blue-600 shrink-0" />
                                <span>{t('Document Under Processing')}</span>
                            </p>
                            <p className="text-blue-800 leading-relaxed">
                                {Number(request.fee_amount ?? 0) > 0
                                    ? `Assessment fee is ₱${Number(request.fee_amount).toFixed(2)}. `
                                    : 'The fee is pending staff assessment. '}
                                Official payment instructions and recipient details will become available once staff process and approve your document and mark it Ready for Pickup.
                            </p>
                        </div>
                    )}

                    {/* Cash Instructions Banner (REV-07) */}
                    {canChoosePayment && (
                        <div className="space-y-1.5">
                            <label className="block text-xs font-semibold text-slate-700">
                                {t('Choose payment method')}
                                <select
                                    value={selectedPaymentChoice}
                                    disabled={choosingPayment || recipientsLoading && Boolean(request.payment_recipient)}
                                    onChange={(event) => {
                                        if (event.target.value) onChoosePaymentMethod?.(event.target.value);
                                    }}
                                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs disabled:opacity-60"
                                >
                                    <option value="">{t('Select how you will pay')}</option>
                                    <option value="CASH">{t('Cash at barangay hall')}</option>
                                    {recipients.map((recipient) => (
                                        <option key={recipient.id} value={`RECIPIENT:${recipient.id}`}>
                                            {recipient.provider_label} · {recipient.display_name}
                                        </option>
                                    ))}
                                </select>
                            </label>
                            {recipientsLoadError && (
                                <div role="alert" className="flex items-center justify-between gap-2 text-[11px] text-rose-700">
                                    <span>{t('Could not load your barangay e-payment options. Cash remains available.')}</span>
                                    <button type="button" aria-label={t('Retry payment option loading')} onClick={onRetryRecipients} className="font-semibold underline">
                                        {t('Retry')}
                                    </button>
                                </div>
                            )}
                            {recipientsLoading && !recipientsLoadError && (
                                <p role="status" className="text-[11px] text-slate-500">{t('Loading barangay e-payment options…')}</p>
                            )}
                            {!recipientsLoading && !recipientsLoadError && recipients.length === 0 && (
                                <p className="text-[11px] text-slate-600">{t('No e-payment options are configured. Cash at the Barangay Hall is the only available method.')}</p>
                            )}
                        </div>
                    )}

                    {!isPaymentNotRequired && isCash && (
                        <div className="p-3 rounded-xl border border-amber-200 bg-amber-50/60 text-xs text-amber-900 space-y-1">
                            <p className="font-semibold">{t('Payment Method: Cash')}</p>
                            <p className="text-amber-800 leading-relaxed">
                                Please proceed to the Barangay Treasurer desk to pay ₱{Number(request.fee_amount).toFixed(2)} upon document pickup. No online upload required.
                            </p>
                        </div>
                    )}

                    {!isStatutoryFeeExempt && !isStaffWaived && isPaymentNotRequired &&
                        ['READY_FOR_PICKUP', 'RELEASED'].includes(request.status.toUpperCase()) && (
                            <p className="text-xs font-semibold text-emerald-800">{t('No payment required')}</p>
                        )}

                    {/* Assessed electronic payment lifecycle */}
                    {!isPaymentNotRequired && !isCash && isElectronicPayment && (
                        <div className="space-y-1.5 text-xs text-slate-600">
                            <p>{t('Assessment')}: ₱{Number(request.fee_amount).toFixed(2)}</p>

                            {/* Pending Verification Banner */}
                            {request.status.toUpperCase() === 'READY_FOR_PICKUP' &&
                                request.payment_status === 'PENDING_VERIFICATION' && (
                                    <div className="p-3 rounded-xl border border-amber-200 bg-amber-50 text-xs text-amber-900 space-y-1">
                                        <p className="font-semibold flex items-center gap-1.5">
                                            <Clock className="w-4 h-4 text-amber-600 shrink-0" />
                                            <span>{t('Payment submitted and awaiting staff verification.')}</span>
                                        </p>
                                        <p className="text-amber-800">
                                            {t('Transfer Reference')}: <span className="font-mono font-bold">{request.payment_reference || '—'}</span>
                                            {request.payment_transacted_at && (
                                                <span> · {t('Transacted at')}: {formatDateTime(request.payment_transacted_at)}</span>
                                            )}
                                        </p>
                                        {request.payment_proof_url && (
                                            <button
                                                type="button"
                                                onClick={() => setIsPreviewOpen(true)}
                                                className="mt-1.5 inline-flex items-center gap-1.5 text-[11px] font-semibold text-amber-900 hover:text-amber-950 underline cursor-pointer"
                                            >
                                                <ImageIcon className="w-3.5 h-3.5" />
                                                <span>{t('View submitted receipt')}</span>
                                            </button>
                                        )}
                                    </div>
                                )}

                            {/* Rejected State & Resubmission Flow */}
                            {request.status.toUpperCase() === 'READY_FOR_PICKUP' &&
                                request.payment_status === 'REJECTED' && (
                                    <div className="space-y-2">
                                        <div className="p-3 rounded-xl border border-rose-200 bg-rose-50 text-xs text-rose-800">
                                            <p className="font-bold flex items-center gap-1.5">
                                                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                                                <span>{t('Payment Reference Rejected')}</span>
                                            </p>
                                            {request.payment_review_note && (
                                                <p className="mt-1 text-rose-700">{t('Staff Note')}: {request.payment_review_note}</p>
                                            )}
                                        </div>
                                        {!isRetrying ? (
                                            <button
                                                type="button"
                                                onClick={() => setIsRetrying(true)}
                                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-100 hover:bg-rose-200 text-rose-800 text-xs font-bold border border-rose-300 transition-colors cursor-pointer"
                                            >
                                                <span>{t('Resubmit Payment Evidence')}</span>
                                            </button>
                                        ) : (
                                            <PaymentReferenceForm
                                                requestId={request.id}
                                                recipients={recipients}
                                                recipientsLoading={recipientsLoading}
                                                recipientsLoadError={recipientsLoadError}
                                                onRetryRecipients={onRetryRecipients}
                                                submitting={submittingPayment}
                                                selectedRecipientId={String(request.payment_recipient)}
                                                hideRecipientSelection
                                                initialReference={request.payment_reference || paymentReference}
                                                initialTransactedAt={request.payment_transacted_at || ''}
                                                onSubmit={onSubmitPaymentReference}
                                                onCancel={() => setIsRetrying(false)}
                                            />
                                        )}
                                    </div>
                                )}

                            {/* Unpaid Initial Submission Form */}
                            {request.status.toUpperCase() === 'READY_FOR_PICKUP' &&
                                (!request.payment_status || request.payment_status === 'UNPAID') && (
                                    <PaymentReferenceForm
                                        requestId={request.id}
                                        recipients={recipients}
                                        recipientsLoading={recipientsLoading}
                                        recipientsLoadError={recipientsLoadError}
                                        onRetryRecipients={onRetryRecipients}
                                        submitting={submittingPayment}
                                        selectedRecipientId={String(request.payment_recipient)}
                                        paymentReference={paymentReference}
                                        hideRecipientSelection
                                        onPaymentReferenceChange={onPaymentReferenceChange}
                                        initialRecipientId={String(request.payment_recipient)}
                                        initialReference={paymentReference}
                                        onSubmit={onSubmitPaymentReference}
                                    />
                                )}
                        </div>
                    )}

                    {request.admin_notes && (
                        <p className="text-[11px] text-slate-500 mt-1 italic">
                            {t('Note')}: {request.admin_notes}
                        </p>
                    )}
                </td>
                <td className="py-4 px-6 text-right">
                    <div className="flex flex-col items-end gap-2">
                        <button
                            type="button"
                            onClick={onGetCounterTicket}
                            disabled={requestingCounterTicket}
                            aria-label={`${t('Get counter ticket for document request')} #${request.id}`}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-800 hover:bg-blue-100 text-xs font-bold border border-blue-200 transition-all cursor-pointer disabled:opacity-60"
                        >
                            {requestingCounterTicket
                                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                : <Ticket className="w-3.5 h-3.5" />}
                            <span>{t('Get counter ticket')}</span>
                        </button>
                        {isAvailableForDownload ? (
                            <>
                                {request.status.toUpperCase() === 'READY_FOR_PICKUP' &&
                                    request.payment_status === 'PENDING_VERIFICATION' && (
                                        <span className="text-xs font-medium text-amber-700">{t('Waiting for payment verification')}</span>
                                    )}
                                <button
                                    onClick={onDownloadPdf}
                                    disabled={downloading}
                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 text-xs font-bold border border-emerald-200 transition-all cursor-pointer"
                                >
                                    {downloading ? (
                                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    ) : (
                                        <Download className="w-3.5 h-3.5" />
                                    )}
                                    <span>{t('Download PDF')}</span>
                                </button>
                            </>
                        ) : request.status.toUpperCase() === 'PENDING' ? (
                        <button
                            onClick={onCancel}
                            disabled={cancelling}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-50 text-rose-700 hover:bg-rose-100 text-xs font-bold border border-rose-200 transition-all cursor-pointer"
                            aria-label={`${t('Cancel clearance request')} #${request.id}`}
                        >
                            {cancelling ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                                <Trash2 className="w-3.5 h-3.5" />
                            )}
                            <span>{t('Cancel')}</span>
                        </button>
                        ) : (
                            <span className="text-xs text-slate-400">{t('Available after approval')}</span>
                        )}
                    </div>
                </td>
            </tr>

            {/* Receipt Inspection Modal */}
            <ProofPreviewModal
                isOpen={isPreviewOpen}
                proofUrl={request.payment_proof_url || null}
                reference={request.payment_reference}
                onClose={() => setIsPreviewOpen(false)}
            />
        </>
    );
};
