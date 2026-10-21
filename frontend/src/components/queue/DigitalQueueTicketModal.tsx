import React, { useId } from 'react';
import { Loader2, X } from 'lucide-react';
import { useModalFocus } from '../../hooks/useModalFocus';
import { useLanguage } from '../../context/language-context';

export interface DigitalQueueTicketModalProps {
    onClose: () => void;
    onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
    serviceType: string;
    setServiceType: (type: string) => void;
    serviceTypes: string[];
    submitting: boolean;
}

export const DigitalQueueTicketModal: React.FC<DigitalQueueTicketModalProps> = ({
    onClose,
    onSubmit,
    serviceType,
    setServiceType,
    serviceTypes,
    submitting,
}) => {
    const dialogTitleId = useId();
    const dialogRef = useModalFocus<HTMLDivElement>(true, onClose);
    const { t } = useLanguage();

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
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
                        {t('Generate Digital Queue Ticket')}
                    </h3>
                    <button
                        onClick={onClose}
                        type="button"
                        aria-label={t('Close queue ticket form')}
                        className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={onSubmit} className="mt-4 space-y-4">
                    <div>
                        <label htmlFor="queue-service-type" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                            {t('Select Service')}
                        </label>
                        <select
                            id="queue-service-type"
                            value={serviceType}
                            onChange={(e) => setServiceType(e.target.value)}
                            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-[#F8FAFD] text-sm text-slate-800 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                        >
                            {serviceTypes.map((type) => (
                                <option key={type} value={type}>
                                    {t(type)}
                                </option>
                            ))}
                        </select>
                    </div>

                    <p className="text-xs leading-relaxed text-slate-600">
                        {t('Barangay staff verify priority lane eligibility. If you qualify, ask the service desk to review your waiting ticket.')}
                    </p>

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
                            <span>{submitting ? t('Generating...') : t('Confirm Ticket')}</span>
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
