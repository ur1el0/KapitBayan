import React from 'react';
import { Loader2, X } from 'lucide-react';
import { DOCUMENT_TYPES } from './documentTypes';
import { useModalFocus } from '../../hooks/useModalFocus';
import { useLanguage } from '../../context/language-context';

interface NewDocumentRequestModalProps {
    documentType: string;
    purpose: string;
    submitting: boolean;
    onDocumentTypeChange: (value: string) => void;
    onPurposeChange: (value: string) => void;
    onClose: () => void;
    onSubmit: (event: React.SubmitEvent<HTMLElement>) => void;
}

export const NewDocumentRequestModal: React.FC<NewDocumentRequestModalProps> = ({
    documentType,
    purpose,
    submitting,
    onDocumentTypeChange,
    onPurposeChange,
    onClose,
    onSubmit,
}) => {
    const { t } = useLanguage();
    const dialogTitleId = React.useId();
    const dialogRef = useModalFocus<HTMLDivElement>(true, onClose);

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
                    {t('Request Official Clearance')}
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
                        value={documentType}
                        onChange={(event) => onDocumentTypeChange(event.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-[#F8FAFD] text-sm text-slate-800 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                    >
                        {DOCUMENT_TYPES.map((type) => (
                            <option key={type} value={type}>
                                {type}
                            </option>
                        ))}
                    </select>
                </div>

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
                        {t('Required by law. This will be printed on your official barangay certificate.')}
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
