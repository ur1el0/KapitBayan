import React from 'react';
import { Loader2, X } from 'lucide-react';
import {
    formatPublishedFee,
    OTHER_DOCUMENT_TYPE,
    type DocumentServiceOffering,
} from '../documents/documentCatalog';
import { useModalFocus } from '../../hooks/useModalFocus';
import { useLanguage } from '../../context/language-context';

interface NewDocumentRequestModalProps {
    offerings?: DocumentServiceOffering[];
    offeringId?: number | null;
    offeringsLoadError?: boolean;
    documentType?: string;
    purpose: string;
    otherDocumentType: string;
    submitting: boolean;
    onOfferingChange?: (value: number | null) => void;
    onDocumentTypeChange?: (value: string) => void;
    onOtherDocumentTypeChange: (value: string) => void;
    onPurposeChange: (value: string) => void;
    onClose: () => void;
    onSubmit: (event: React.SubmitEvent<HTMLElement>) => void;
}

export const NewDocumentRequestModal: React.FC<NewDocumentRequestModalProps> = ({
    offerings = [],
    offeringId,
    offeringsLoadError = false,
    documentType,
    purpose,
    otherDocumentType,
    submitting,
    onOfferingChange,
    onDocumentTypeChange,
    onOtherDocumentTypeChange,
    onPurposeChange,
    onClose,
    onSubmit,
}) => {
    const { t } = useLanguage();
    const dialogTitleId = React.useId();
    const dialogRef = useModalFocus<HTMLDivElement>(true, onClose);
    const selectedOffering = offerings.find((offering) => offering.id === offeringId);
    const isOtherSelected = selectedOffering
        ? false
        : documentType !== undefined
            ? documentType === OTHER_DOCUMENT_TYPE
            : offeringId == null;

    return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
        <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={dialogTitleId}
            tabIndex={-1}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150"
        >
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <h3 id={dialogTitleId} className="text-lg font-extrabold text-slate-900">
                    {t('Request a document')}
                </h3>
                <button
                    onClick={onClose}
                    aria-label={t('Close request modal')}
                    className="text-slate-400 hover:text-slate-600 rounded-lg p-1"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>

            <form onSubmit={onSubmit} className="mt-4 space-y-4">
                <div>
                    <label htmlFor="document-type" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                        {t('Document Type')}
                    </label>
                    <select
                        id="document-type"
                        value={selectedOffering ? String(selectedOffering.id) : (documentType ?? OTHER_DOCUMENT_TYPE)}
                        onChange={(event) => {
                            const value = event.target.value;
                            if (onOfferingChange) {
                                onOfferingChange(value === OTHER_DOCUMENT_TYPE ? null : Number(value));
                            } else {
                                onDocumentTypeChange?.(value);
                            }
                        }}
                        className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-[#F8FAFD] text-sm text-slate-800 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                    >
                        {offerings.map((offering) => (
                            <option key={offering.id} value={offering.id}>
                                {t(offering.document_type)}
                            </option>
                        ))}
                        <option value={OTHER_DOCUMENT_TYPE}>{t(OTHER_DOCUMENT_TYPE)}</option>
                    </select>
                </div>

                {selectedOffering && (
                    <div className="rounded-xl border border-blue-100 bg-blue-50/70 p-3 text-xs text-slate-700 space-y-2">
                        <p className="font-semibold text-slate-900">
                            {t('Published fee')}: {t(formatPublishedFee(selectedOffering.published_fee_amount))}
                        </p>
                        {selectedOffering.requirements.length > 0 ? (
                            <div>
                                <p className="font-semibold">{t('Bring these requirements')}:</p>
                                <ul className="list-disc pl-5 mt-1 space-y-0.5">
                                    {selectedOffering.requirements.map((requirement, index) => (
                                        <li key={`${index}-${requirement}`}>{t(requirement)}</li>
                                    ))}
                                </ul>
                            </div>
                        ) : (
                            <p>{t('Your Barangay has not published requirements for this service yet.')}</p>
                        )}
                        {selectedOffering.details && <p>{t(selectedOffering.details)}</p>}
                        <p className="text-slate-500">{t('Final fees are confirmed by Barangay staff during processing.')}</p>
                    </div>
                )}

                {isOtherSelected && (
                    <div>
                        <label htmlFor="other-document-type" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                            {t('Document name')}
                        </label>
                        <input
                            id="other-document-type"
                            type="text"
                            required
                            maxLength={100}
                            value={otherDocumentType}
                            onChange={(event) => onOtherDocumentTypeChange(event.target.value)}
                            placeholder={t('Enter the barangay document name')}
                            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-[#F8FAFD] text-sm text-slate-800 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                        />
                        <p className="text-[11px] text-slate-500 mt-1">
                            {t('Confirm availability and requirements with your Barangay.')}
                        </p>
                    </div>
                )}

                {offeringsLoadError && (
                    <p className="text-xs text-rose-700" role="alert">
                        {t("We couldn't load your Barangay's document services. You can still enter a document name, but staff will need to confirm its requirements.")}
                    </p>
                )}

                {offerings.length === 0 && !offeringsLoadError && (
                    <p className="text-xs text-amber-700" role="status">
                        {t('Your Barangay has not published its document services yet. The request will need staff confirmation.')}
                    </p>
                )}

                <div>
                    <label htmlFor="document-purpose" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                        {t('Purpose Statement')}
                    </label>
                    <input
                        id="document-purpose"
                        type="text"
                        required
                        placeholder={t('e.g. Local Employment, Scholarship, Postal ID')}
                        value={purpose}
                        onChange={(event) => onPurposeChange(event.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-[#F8FAFD] text-sm text-slate-800 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                        {t('Tell the Barangay why you need this document.')}
                    </p>
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-all cursor-pointer"
                    >
                        {t('Cancel')}
                    </button>
                    <button
                        type="submit"
                        disabled={submitting}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary hover:bg-primary-hover text-primary-foreground text-xs font-bold shadow-xs transition-all cursor-pointer disabled:opacity-50"
                    >
                        {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                        <span>{t(submitting ? 'Submitting...' : 'Submit Application')}</span>
                    </button>
                </div>
            </form>
        </div>
    </div>
    );
};
