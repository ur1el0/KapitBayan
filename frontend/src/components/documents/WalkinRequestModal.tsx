import React, { useId } from 'react';
import { useModalFocus } from '../../hooks/useModalFocus';
import { useLanguage } from '../../context/language-context';
import {
    formatPublishedFee,
    OTHER_DOCUMENT_TYPE,
    type DocumentServiceOffering,
} from './documentCatalog';

export interface WalkinRequestModalProps {
    onClose: () => void;
    onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
    walkinName: string;
    setWalkinName: (name: string) => void;
    walkinPurok: string;
    setWalkinPurok: (purok: string) => void;
    offerings: DocumentServiceOffering[];
    selectedOfferingId: number | null;
    setSelectedOfferingId: (id: number | null) => void;
    newDocType: string;
    setNewDocType: (type: string) => void;
    newPurpose: string;
    setNewPurpose: (purpose: string) => void;
    isSubmitting: boolean;
}

export const WalkinRequestModal: React.FC<WalkinRequestModalProps> = ({
    onClose,
    onSubmit,
    walkinName,
    setWalkinName,
    walkinPurok,
    setWalkinPurok,
    offerings,
    selectedOfferingId,
    setSelectedOfferingId,
    newDocType,
    setNewDocType,
    newPurpose,
    setNewPurpose,
    isSubmitting,
}) => {
    const { t } = useLanguage();
    const walkinDialogTitleId = useId();
    const walkinDialogRef = useModalFocus<HTMLDivElement>(true, onClose);
    const selectedOffering = offerings.find((offering) => offering.id === selectedOfferingId);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
            <div
                ref={walkinDialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby={walkinDialogTitleId}
                tabIndex={-1}
                className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95"
            >
                <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                    <div>
                        <h3 id={walkinDialogTitleId} className="text-base font-bold text-slate-900">{t('Create Walk-in Request')}</h3>
                        <p className="text-xs text-slate-500">{t("Record an in-person resident's document request for staff review.")}</p>
                    </div>
                    <button
                        onClick={onClose}
                        type="button"
                        aria-label={t('Close walk-in request dialog')}
                        className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/60 transition-colors cursor-pointer"
                    >
                        <span className="text-2xl leading-none">&times;</span>
                    </button>
                </div>

                <form onSubmit={onSubmit} className="p-6 space-y-4 bg-white">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                            <label htmlFor="walkin-resident-name" className="block text-xs font-bold text-slate-700 mb-1">{t('Resident Full Name')} *</label>
                            <input
                                id="walkin-resident-name"
                                type="text"
                                required
                                value={walkinName}
                                onChange={(e) => setWalkinName(e.target.value)}
                                placeholder={t('e.g. Maria Santos')}
                                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                            />
                        </div>
                        <div>
                            <label htmlFor="walkin-purok" className="block text-xs font-bold text-slate-700 mb-1">{t('Purok / Zone')}</label>
                            <input
                                id="walkin-purok"
                                type="text"
                                value={walkinPurok}
                                onChange={(e) => setWalkinPurok(e.target.value)}
                                placeholder={t('e.g. Purok Maligaya')}
                                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                            />
                        </div>
                    </div>

                    <div>
                        <label htmlFor="walkin-document-type" className="block text-xs font-bold text-slate-700 mb-1">{t('Document Type')}</label>
                        <select
                            id="walkin-document-type"
                            value={selectedOffering ? String(selectedOffering.id) : OTHER_DOCUMENT_TYPE}
                            onChange={(e) => {
                                const value = e.target.value;
                                setSelectedOfferingId(value === OTHER_DOCUMENT_TYPE ? null : Number(value));
                            }}
                            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary font-medium"
                        >
                            {offerings.map((offering) => (
                                <option key={offering.id} value={offering.id}>{t(offering.document_type)}</option>
                            ))}
                            <option value={OTHER_DOCUMENT_TYPE}>{t(OTHER_DOCUMENT_TYPE)}</option>
                        </select>
                    </div>

                    {selectedOffering ? (
                        <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 text-xs text-slate-700 space-y-1.5">
                            <p className="font-semibold">{t('Published fee')}: {t(formatPublishedFee(selectedOffering.published_fee_amount))}</p>
                            {selectedOffering.requirements.length > 0 && <div><p className="font-semibold">{t('Requirements')}:</p><ul className="list-disc pl-5">{selectedOffering.requirements.map((requirement) => <li key={requirement}>{t(requirement)}</li>)}</ul></div>}
                            {selectedOffering.details && <p>{t(selectedOffering.details)}</p>}
                            <p className="text-slate-500">{t('Final fees are confirmed by Barangay staff during processing.')}</p>
                        </div>
                    ) : (
                        <div>
                            <label htmlFor="walkin-custom-document-type" className="block text-xs font-bold text-slate-700 mb-1">{t('Other document name')} *</label>
                            <input
                                id="walkin-custom-document-type"
                                type="text"
                                required
                                maxLength={100}
                                value={newDocType}
                                onChange={(event) => setNewDocType(event.target.value)}
                                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                            />
                        </div>
                    )}

                    <div>
                        <label htmlFor="walkin-purpose" className="block text-xs font-bold text-slate-700 mb-1">{t('Purpose Statement')} *</label>
                        <textarea
                            id="walkin-purpose"
                            required
                            value={newPurpose}
                            onChange={(e) => setNewPurpose(e.target.value)}
                            rows={2}
                            placeholder={t('e.g. Employment requirement, Bank account opening, Scholarship...')}
                            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                        />
                    </div>

                    <div className="pt-3 flex justify-end gap-2.5">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800 rounded-xl transition-colors"
                        >
                            {t('Cancel')}
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="px-5 py-2 text-sm font-bold text-primary-foreground bg-primary hover:bg-primary-hover rounded-xl transition-all shadow-sm disabled:opacity-70 cursor-pointer"
                        >
                            {isSubmitting ? t('Submitting…') : t('Record Walk-in Request')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
