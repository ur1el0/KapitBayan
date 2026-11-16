import React, { useEffect, useState } from 'react';
import { Wifi, WifiOff } from 'lucide-react';
import { useLanguage } from '../../context/language-context';

export const OfflineBanner: React.FC = () => {
    const { t } = useLanguage();
    const [isOffline, setIsOffline] = useState(!navigator.onLine);
    const [justReconnected, setJustReconnected] = useState(false);

    useEffect(() => {
        const handleOffline = () => {
            setIsOffline(true);
            setJustReconnected(false);
        };

        const handleOnline = () => {
            setIsOffline(false);
            setJustReconnected(true);
            const timer = setTimeout(() => {
                setJustReconnected(false);
            }, 3000);
            return () => clearTimeout(timer);
        };

        window.addEventListener('offline', handleOffline);
        window.addEventListener('online', handleOnline);

        return () => {
            window.removeEventListener('offline', handleOffline);
            window.removeEventListener('online', handleOnline);
        };
    }, []);

    if (!isOffline && !justReconnected) {
        return null;
    }

    if (justReconnected) {
        return (
            <aside
                role="status"
                aria-live="polite"
                className="bg-emerald-600 px-4 py-2.5 text-center text-sm font-semibold text-white shadow-sm transition-all animate-in fade-in slide-in-from-top-2 print:hidden"
            >
                <div className="mx-auto flex max-w-7xl items-center justify-center gap-2">
                    <Wifi className="h-4 w-4" aria-hidden="true" />
                    <span>{t('Back online. Connection restored.')}</span>
                </div>
            </aside>
        );
    }

    return (
        <aside
            role="status"
            aria-live="polite"
            className="bg-amber-600 px-4 py-2.5 text-center text-sm font-semibold text-amber-50 shadow-sm transition-all print:hidden"
        >
            <div className="mx-auto flex max-w-7xl items-center justify-center gap-2">
                <WifiOff className="h-4 w-4 shrink-0 text-amber-200" aria-hidden="true" />
                <span>
                    {t('You are currently offline. Cached views remain available; new requests require an active connection.')}
                </span>
            </div>
        </aside>
    );
};
