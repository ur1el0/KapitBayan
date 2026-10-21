import React from 'react';
import { useLanguage } from '../../../context/language-context';

export interface PublicBarangay {
    id: number;
    name: string;
    municipality: string;
    province: string;
}

interface BarangaySelectFieldProps {
    barangayId: string;
    onBarangayIdChange: (val: string) => void;
    barangays: PublicBarangay[];
    loadingBarangays: boolean;
    barangayDirectoryError?: string;
    onRetry: () => void;
    isAdminMode: boolean;
}

export const BarangaySelectField: React.FC<BarangaySelectFieldProps> = ({
    barangayId,
    onBarangayIdChange,
    barangays,
    loadingBarangays,
    barangayDirectoryError,
    onRetry,
    isAdminMode,
}) => {
    const barangayIdFieldId = React.useId();
    const { t } = useLanguage();

    return (
        <div>
            <div>
                <label
                    htmlFor={barangayIdFieldId}
                    className="block text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-1.5"
                >
                    {t('LOCAL BARANGAY JURISDICTION')}
                </label>
                <select
                    id={barangayIdFieldId}
                    required
                    value={barangayId}
                    disabled={loadingBarangays || barangays.length === 0}
                    onChange={(e) => onBarangayIdChange(e.target.value)}
                    className={`w-full px-4 py-3 bg-[#EEF2F6] focus:bg-white border border-transparent rounded-xl text-sm font-medium text-slate-900 outline-none transition-all cursor-pointer disabled:cursor-not-allowed disabled:opacity-60 ${
                        isAdminMode ? 'focus:border-[#091B35] focus:ring-1 focus:ring-[#091B35]' : 'focus:border-[#0284C7]'
                    }`}
                >
                    <option value="">{loadingBarangays ? t('Loading approved barangays…') : t('Select your Barangay')}</option>
                    {barangays.map((barangay) => (
                        <option key={barangay.id} value={barangay.id}>
                            {barangay.name}{barangay.municipality ? ` (${barangay.municipality}${barangay.province ? `, ${barangay.province}` : ''})` : ''}
                        </option>
                    ))}
                </select>
                {loadingBarangays && !barangayDirectoryError && (
                    <p role="status" aria-live="polite" className="sr-only">
                        {t('Loading approved barangay list…')}
                    </p>
                )}
                {barangayDirectoryError && (
                    <div role="alert" className="mt-2 flex flex-wrap items-center gap-3 text-xs text-rose-700">
                        <p>{barangayDirectoryError}</p>
                        <button
                            type="button"
                            aria-label={t('Retry approved barangay list')}
                            onClick={onRetry}
                            disabled={loadingBarangays}
                            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border border-rose-300 px-3 font-semibold text-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 disabled:cursor-wait disabled:opacity-60"
                        >
                            {loadingBarangays ? t('Retrying…') : t('Try again')}
                        </button>
                        {loadingBarangays && (
                            <span role="status" aria-live="polite" className="sr-only">
                                {t('Retrying approved barangay list…')}
                            </span>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};
