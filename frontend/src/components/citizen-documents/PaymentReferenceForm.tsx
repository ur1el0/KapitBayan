import React, { useEffect, useState } from 'react';
import { AlertCircle, Calendar, Loader2, Upload, X } from 'lucide-react';
import type { PaymentRecipient } from './types';
import { useLanguage } from '../../context/language-context';

export interface PaymentReferenceFormProps {
    requestId: number;
    recipients: PaymentRecipient[];
    recipientsLoading: boolean;
    recipientsLoadError: boolean;
    onRetryRecipients: () => void;
    submitting: boolean;
    selectedRecipientId?: string;
    paymentReference?: string;
    onRecipientChange?: (value: string) => void;
    onPaymentReferenceChange?: (value: string) => void;
    initialRecipientId?: string;
    initialReference?: string;
    initialTransactedAt?: string;
    onSubmit: (formData: FormData) => void | Promise<void>;
    onCancel?: () => void;
}

export const PaymentReferenceForm: React.FC<PaymentReferenceFormProps> = ({
    requestId,
    recipients,
    recipientsLoading,
    recipientsLoadError,
    onRetryRecipients,
    submitting,
    selectedRecipientId: controlledRecipientId,
    paymentReference: controlledReference,
    onRecipientChange,
    onPaymentReferenceChange,
    initialRecipientId = '',
    initialReference = '',
    initialTransactedAt = '',
    onSubmit,
    onCancel,
}) => {
    const { t } = useLanguage();
    const [internalRecipientId, setInternalRecipientId] = useState<string>(
        controlledRecipientId || initialRecipientId,
    );
    const [internalReference, setInternalReference] = useState<string>(
        controlledReference || initialReference,
    );

    const activeRecipientId = controlledRecipientId !== undefined ? controlledRecipientId : internalRecipientId;
    const activeReference = controlledReference !== undefined ? controlledReference : internalReference;

    const [paymentTransactedAt, setPaymentTransactedAt] = useState<string>(() => {
        if (initialTransactedAt) {
            try {
                const d = new Date(initialTransactedAt);
                if (!isNaN(d.getTime())) {
                    const pad = (n: number) => String(n).padStart(2, '0');
                    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
                }
            } catch {
                // fallback below
            }
        }
        const now = new Date();
        const pad = (n: number) => String(n).padStart(2, '0');
        return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
    });

    const [proofFile, setProofFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [validationError, setValidationError] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    useEffect(() => {
        if (initialRecipientId && !controlledRecipientId) {
            setInternalRecipientId(initialRecipientId);
        }
        if (initialReference && controlledReference === undefined) {
            setInternalReference(initialReference);
        }
    }, [initialRecipientId, initialReference, controlledRecipientId, controlledReference]);

    useEffect(() => {
        return () => {
            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
            }
        };
    }, [previewUrl]);

    const handleFileChange = (file: File | null) => {
        setValidationError(null);
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            setPreviewUrl(null);
        }
        if (!file) {
            setProofFile(null);
            return;
        }

        const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            setValidationError(t('Only JPEG, PNG, and WEBP image formats are supported.'));
            return;
        }

        const maxSize = 5 * 1024 * 1024; // 5 MB
        if (file.size > maxSize) {
            setValidationError(t('Payment proof screenshot must not exceed 5 MB.'));
            return;
        }

        setProofFile(file);
        setPreviewUrl(URL.createObjectURL(file));
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) {
            handleFileChange(file);
        }
    };

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setValidationError(null);

        if (!activeRecipientId) {
            setValidationError(t('Please select an active payment recipient configured by your barangay.'));
            return;
        }

        const trimmedRef = activeReference.trim();
        if (!trimmedRef || trimmedRef.length < 3) {
            setValidationError(t('Transfer reference must be at least 3 characters.'));
            return;
        }

        if (!paymentTransactedAt) {
            setValidationError(t('Please provide the transaction date and time.'));
            return;
        }

        const transactedDate = new Date(paymentTransactedAt);
        const now = new Date();
        const fiveMinutesFuture = new Date(now.getTime() + 5 * 60 * 1000);
        if (transactedDate > fiveMinutesFuture) {
            setValidationError(t('Transaction timestamp cannot be in the future.'));
            return;
        }

        if (!proofFile) {
            setValidationError(t('Please upload a screenshot of your payment receipt.'));
            return;
        }

        const formData = new FormData();
        formData.append('payment_recipient_id', activeRecipientId);
        formData.append('payment_reference', trimmedRef);
        formData.append('payment_transacted_at', transactedDate.toISOString());
        formData.append('payment_proof_image', proofFile);

        onSubmit(formData);
    };

    const selectedRecipient = recipients.find(
        (recipient) => recipient.id === Number(activeRecipientId),
    );

    return (
        <form className="mt-3 space-y-3 rounded-xl border border-slate-200 bg-slate-50/60 p-4 text-xs" onSubmit={handleSubmit}>
            <p className="text-slate-600 font-medium">
                {t('Select an official recipient configured by your barangay, follow instructions, enter your transfer reference and date/time, and attach a screenshot of your receipt. Staff verify the transfer manually.')}
            </p>

            {recipientsLoading && !recipientsLoadError ? (
                <p
                    role="status"
                    aria-live="polite"
                    className="flex items-center gap-2 rounded-lg bg-slate-100 p-3 text-xs text-slate-700"
                >
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    {t('Loading payment recipients…')}
                </p>
            ) : recipientsLoadError ? (
                <div className="space-y-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
                    <p role="alert" id={`payment-recipient-error-${requestId}`}>
                        {t("We couldn't load payment recipients. Please try again.")}
                    </p>
                    {recipientsLoading && (
                        <p role="status" className="sr-only">
                            {t('Retrying payment recipients…')}
                        </p>
                    )}
                    <button
                        type="button"
                        onClick={onRetryRecipients}
                        disabled={recipientsLoading}
                        aria-describedby={`payment-recipient-error-${requestId}`}
                        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-rose-300 bg-white px-3 py-2 font-semibold text-rose-800 hover:bg-rose-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-700 disabled:cursor-wait disabled:opacity-60"
                    >
                        {recipientsLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
                        {recipientsLoading ? t('Retrying…') : t('Retry payment recipient loading')}
                    </button>
                </div>
            ) : recipients.length === 0 ? (
                <p role="status" className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900 border border-amber-200">
                    {t('Your barangay has not configured an e-payment recipient. Contact the barangay hall or pay in person at the treasurer desk.')}
                </p>
            ) : (
                <>
                    {/* Recipient Dropdown */}
                    <label className="block text-xs font-semibold text-slate-700">
                        {t('Payment recipient')}
                        <select
                            required
                            aria-label={`${t('Payment recipient for request')} ${requestId}`}
                            value={activeRecipientId}
                            onChange={(event) => {
                                const val = event.target.value;
                                setInternalRecipientId(val);
                                onRecipientChange?.(val);
                            }}
                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:ring-2 focus:ring-primary focus:outline-none"
                        >
                            <option value="">{t('Select a recipient')}</option>
                            {recipients.map((recipient) => (
                                <option key={recipient.id} value={recipient.id}>
                                    {recipient.display_name} · {recipient.provider_label}
                                </option>
                            ))}
                        </select>
                    </label>

                    {/* Recipient Details Card */}
                    {selectedRecipient && (
                        <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-700 space-y-1">
                            <p className="font-bold text-slate-900">{selectedRecipient.recipient_name}</p>
                            <p className="font-mono text-slate-600">{selectedRecipient.recipient_identifier}</p>
                            {selectedRecipient.instructions && (
                                <p className="text-slate-500 italic mt-1">{selectedRecipient.instructions}</p>
                            )}
                        </div>
                    )}

                    {/* Reference Input */}
                    <label className="block text-xs font-semibold text-slate-700">
                        {t('Transfer Reference')}
                        <input
                            required
                            maxLength={100}
                            minLength={3}
                            aria-label={`${t('Transfer reference for request')} ${requestId}`}
                            value={activeReference}
                            onChange={(event) => {
                                const val = event.target.value;
                                setInternalReference(val);
                                onPaymentReferenceChange?.(val);
                            }}
                            placeholder={t('Transfer reference (e.g. MP-123456789)')}
                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:ring-2 focus:ring-primary focus:outline-none"
                        />
                    </label>

                    {/* Transaction Date/Time Input */}
                    <label className="block text-xs font-semibold text-slate-700">
                        <span className="flex items-center gap-1.5">
                            <Calendar className="w-3.5 h-3.5 text-slate-500" />
                            {t('Transaction Date and Time (Manila Time)')}
                        </span>
                        <input
                            type="datetime-local"
                            required
                            aria-label={`${t('Transaction date and time for request')} ${requestId}`}
                            value={paymentTransactedAt}
                            onChange={(event) => setPaymentTransactedAt(event.target.value)}
                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:ring-2 focus:ring-primary focus:outline-none"
                        />
                    </label>

                    {/* Screenshot Upload Dropzone */}
                    <div>
                        <span className="block text-xs font-semibold text-slate-700 mb-1">
                            {t('Receipt Screenshot')}
                        </span>
                        <div
                            onDrop={handleDrop}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            className={`relative rounded-xl border-2 border-dashed p-4 text-center transition-all ${
                                isDragging
                                    ? 'border-primary bg-primary/5'
                                    : proofFile
                                    ? 'border-emerald-300 bg-emerald-50/30'
                                    : 'border-slate-300 hover:border-slate-400 bg-white'
                            }`}
                        >
                            {proofFile && previewUrl ? (
                                <div className="flex items-center justify-between gap-3 text-left">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <img
                                            src={previewUrl}
                                            alt={t('Receipt preview thumbnail')}
                                            className="w-12 h-12 object-cover rounded-lg border border-slate-200"
                                        />
                                        <div className="min-w-0">
                                            <p className="font-semibold text-slate-800 truncate text-xs">{proofFile.name}</p>
                                            <p className="text-[11px] text-slate-500">
                                                {(proofFile.size / 1024).toFixed(1)} KB
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => handleFileChange(null)}
                                        aria-label={t('Remove receipt screenshot')}
                                        className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            ) : (
                                <label className="flex flex-col items-center justify-center gap-1.5 cursor-pointer">
                                    <Upload className="w-6 h-6 text-slate-400" />
                                    <span className="text-xs font-semibold text-slate-700">
                                        {t('Click to upload or drag receipt screenshot here')}
                                    </span>
                                    <span className="text-[11px] text-slate-500">
                                        {t('Please ensure your uploaded screenshot visibly shows the transaction reference number, amount, and date/time.')}
                                    </span>
                                    <span className="text-[10px] text-slate-400">
                                        {t('JPEG, PNG, or WEBP (up to 5 MB)')}
                                    </span>
                                    <input
                                        type="file"
                                        accept="image/jpeg,image/png,image/webp"
                                        aria-label={`${t('Payment proof screenshot for request')} ${requestId}`}
                                        className="sr-only"
                                        onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                                    />
                                </label>
                            )}
                        </div>
                    </div>

                    {/* Validation Error Banner */}
                    {validationError && (
                        <div role="alert" className="flex items-center gap-2 rounded-lg bg-rose-50 border border-rose-200 p-2.5 text-xs text-rose-700">
                            <AlertCircle className="w-4 h-4 shrink-0" />
                            <span>{validationError}</span>
                        </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 pt-1">
                        <button
                            type="submit"
                            disabled={submitting}
                            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-xs hover:bg-primary-hover disabled:opacity-50 cursor-pointer"
                        >
                            {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
                            <span>{t(submitting ? 'Submitting…' : 'Submit transfer reference')}</span>
                        </button>
                        {onCancel && (
                            <button
                                type="button"
                                onClick={onCancel}
                                disabled={submitting}
                                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
                            >
                                {t('Cancel')}
                            </button>
                        )}
                    </div>
                </>
            )}
        </form>
    );
};
