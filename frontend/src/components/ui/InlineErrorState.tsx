import React from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { useLanguage } from '../../context/language-context';

interface InlineErrorStateProps {
    message: string;
    onRetry: () => void;
    retrying?: boolean;
}

export const InlineErrorState: React.FC<InlineErrorStateProps> = ({
    message,
    onRetry,
    retrying = false,
}) => {
    const { t } = useLanguage();

    return (
        <div role="alert" className="flex flex-col items-center rounded-2xl border border-rose-200 bg-white p-8 text-center shadow-xs">
        <AlertCircle className="mb-3 h-8 w-8 text-rose-600" aria-hidden="true" />
        <p className="text-sm font-semibold text-slate-900">{message}</p>
        <p className="mt-1 text-sm text-slate-600">{t('Check your connection and try again.')}</p>
        <button
            type="button"
            onClick={onRetry}
            disabled={retrying}
            className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-wait disabled:opacity-60"
        >
            {retrying && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            {retrying ? t('Trying again…') : t('Try again')}
        </button>
        </div>
    );
};
