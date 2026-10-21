import React, { useEffect, useState } from 'react';
import { Plus, Save, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { axiosPrivate } from '../../api/axios';
import { getSafeApiErrorMessage } from '../../api/error-message';
import { useModalFocus } from '../../hooks/useModalFocus';
import { useLanguage } from '../../context/language-context';
import type { DocumentServiceOffering } from './documentCatalog';

interface DocumentCatalogManagerModalProps {
    offerings: DocumentServiceOffering[];
    onClose: () => void;
    onSaved: () => Promise<void> | void;
}

export const DocumentCatalogManagerModal: React.FC<DocumentCatalogManagerModalProps> = ({
    offerings,
    onClose,
    onSaved,
}) => {
    const { t } = useLanguage();
    const dialogRef = useModalFocus<HTMLDivElement>(true, onClose);
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [documentType, setDocumentType] = useState('');
    const [requirementsText, setRequirementsText] = useState('');
    const [publishedFee, setPublishedFee] = useState('');
    const [details, setDetails] = useState('');
    const [isActive, setIsActive] = useState(true);
    const [saving, setSaving] = useState(false);
    const [changingStatusId, setChangingStatusId] = useState<number | null>(null);

    const selectedOffering = offerings.find((offering) => offering.id === selectedId) ?? null;

    const clearForm = () => {
        setSelectedId(null);
        setDocumentType('');
        setRequirementsText('');
        setPublishedFee('');
        setDetails('');
        setIsActive(true);
    };

    useEffect(() => {
        if (!selectedOffering) return;
        setDocumentType(selectedOffering.document_type);
        setRequirementsText(selectedOffering.requirements.join('\n'));
        setPublishedFee(selectedOffering.published_fee_amount ?? '');
        setDetails(selectedOffering.details ?? '');
        setIsActive(selectedOffering.is_active);
    }, [selectedOffering]);

    const handleSave = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const name = documentType.trim();
        const requirements = requirementsText
            .split('\n')
            .map((requirement) => requirement.trim())
            .filter(Boolean);
        const fee = publishedFee.trim();
        if (!name || name.length > 100 || requirements.length > 30 || requirements.some((item) => item.length > 250)) {
            toast.error(t('Enter a document name and up to 30 requirements, each no longer than 250 characters.'));
            return;
        }
        if (fee && (!Number.isFinite(Number(fee)) || Number(fee) < 0 || !/^\d{1,6}(\.\d{1,2})?$/.test(fee))) {
            toast.error(t('Enter a fee from 0 to 999999.99, or leave it blank if it varies.'));
            return;
        }

        setSaving(true);
        try {
            const payload = {
                document_type: name,
                requirements,
                published_fee_amount: fee || null,
                details: details.trim(),
                is_active: isActive,
            };
            if (selectedId) {
                await axiosPrivate.patch(`/document-catalog/${selectedId}/`, payload);
                toast.success(t('Document service updated.'));
            } else {
                await axiosPrivate.post('/document-catalog/', payload);
                toast.success(t('Document service saved.'));
            }
            await onSaved();
            clearForm();
        } catch (error) {
            toast.error(getSafeApiErrorMessage(error, t("We couldn't save this document service.")));
        } finally {
            setSaving(false);
        }
    };

    const handleToggleActive = async (offering: DocumentServiceOffering) => {
        setChangingStatusId(offering.id);
        try {
            await axiosPrivate.patch(`/document-catalog/${offering.id}/`, {
                is_active: !offering.is_active,
            });
            await onSaved();
            if (selectedId === offering.id) setIsActive(!offering.is_active);
            toast.success(offering.is_active ? t('Document service deactivated.') : t('Document service activated.'));
        } catch (error) {
            toast.error(getSafeApiErrorMessage(error, t("We couldn't update this document service.")));
        } finally {
            setChangingStatusId(null);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="document-catalog-title"
                tabIndex={-1}
                className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
            >
                <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
                    <div>
                        <h2 id="document-catalog-title" className="text-lg font-bold text-slate-900">{t('Document services and requirements')}</h2>
                        <p className="mt-1 text-xs text-slate-500">{t('Save an active service to publish its requirements, fee, and details to residents. Later edits apply to new requests.')}</p>
                    </div>
                    <button type="button" onClick={onClose} aria-label={t('Close document catalog')} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100">
                        <X className="h-5 w-5" />
                    </button>
                </div>

                <div className="grid min-h-0 flex-1 gap-5 overflow-y-auto p-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
                    <section aria-label={t('Saved document services')} className="space-y-2">
                        <button type="button" onClick={clearForm} className="flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 text-sm font-semibold text-blue-900 hover:bg-blue-100">
                            <Plus className="h-4 w-4" /> {t('Add document service')}
                        </button>
                        {offerings.length === 0 ? (
                            <p className="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-500">{t('No document services have been added yet.')}</p>
                        ) : offerings.map((offering) => (
                            <div key={offering.id} className={`rounded-lg border p-3 ${selectedId === offering.id ? 'border-blue-400 bg-blue-50/70' : 'border-slate-200'}`}>
                                <div className="flex items-start justify-between gap-3">
                                    <button type="button" onClick={() => setSelectedId(offering.id)} className="min-w-0 flex-1 text-left">
                                        <span className="block truncate text-sm font-semibold text-slate-900">{offering.document_type}</span>
                                        <span className="mt-1 block text-xs text-slate-500">{offering.requirements.length} {t('requirements')} · {offering.published_fee_amount === null ? t('Fee not listed') : `₱${Number(offering.published_fee_amount).toFixed(2)}`}</span>
                                        <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold ${offering.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'}`}>{t(offering.is_active ? 'Active' : 'Inactive')}</span>
                                    </button>
                                    <button type="button" disabled={changingStatusId === offering.id} onClick={() => void handleToggleActive(offering)} className="shrink-0 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-50">
                                        {t(offering.is_active ? 'Deactivate' : 'Activate')}
                                    </button>
                                </div>
                            </div>
                        ))}
                    </section>

                    <form onSubmit={(event) => void handleSave(event)} className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
                        <h3 className="text-sm font-bold text-slate-900">{selectedId ? t('Edit document service') : t('New document service')}</h3>
                        <div>
                            <label htmlFor="catalog-document-type" className="mb-1 block text-xs font-semibold text-slate-700">{t('Document name')}</label>
                            <input id="catalog-document-type" required maxLength={100} value={documentType} onChange={(event) => setDocumentType(event.target.value)} className="min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" />
                        </div>
                        <div>
                            <label htmlFor="catalog-requirements" className="mb-1 block text-xs font-semibold text-slate-700">{t('Requirements, one per line')}</label>
                            <textarea id="catalog-requirements" value={requirementsText} onChange={(event) => setRequirementsText(event.target.value)} maxLength={8000} rows={7} placeholder={t('Example: Government ID or proof of residency')} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" />
                            <p className="mt-1 text-[11px] text-slate-500">{t('Requirements are specific to this document and Barangay. Add each item on a new line.')}</p>
                        </div>
                        <div>
                            <label htmlFor="catalog-published-fee" className="mb-1 block text-xs font-semibold text-slate-700">{t('Published fee amount (PHP)')}</label>
                            <input id="catalog-published-fee" type="number" min="0" max="999999.99" step="0.01" value={publishedFee} onChange={(event) => setPublishedFee(event.target.value)} placeholder={t('Leave blank if it varies or is not published')} className="min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" />
                            <p className="mt-1 text-[11px] text-slate-500">{t('A value of 0 means no fee. The final assessed fee remains recorded on the request.')}</p>
                        </div>
                        <div>
                            <label htmlFor="catalog-details" className="mb-1 block text-xs font-semibold text-slate-700">{t('Additional details')}</label>
                            <textarea id="catalog-details" value={details} onChange={(event) => setDetails(event.target.value)} maxLength={2000} rows={3} placeholder={t('Add preparation, schedule, or payment details')} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" />
                        </div>
                        <label className="flex items-center gap-2 text-sm text-slate-700">
                            <input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} />
                            {t('Available to residents')}
                        </label>
                        <button type="submit" disabled={saving} className="flex min-h-10 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground disabled:opacity-60">
                            <Save className="h-4 w-4" /> {saving ? t('Saving…') : t('Save document service')}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
};
