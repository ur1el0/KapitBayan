import React, { useEffect, useState } from 'react';
import { Download, X } from 'lucide-react';
import { useLanguage } from '../../context/language-context';

interface BeforeInstallPromptEvent extends Event {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export const PwaInstallPrompt: React.FC = () => {
    const { t } = useLanguage();
    const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
    const [dismissed, setDismissed] = useState(false);

    useEffect(() => {
        const handleBeforeInstallPrompt = (event: Event) => {
            event.preventDefault();
            setInstallPrompt(event as BeforeInstallPromptEvent);
        };

        const handleAppInstalled = () => {
            setInstallPrompt(null);
        };

        window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
        window.addEventListener('appinstalled', handleAppInstalled);

        return () => {
            window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
            window.removeEventListener('appinstalled', handleAppInstalled);
        };
    }, []);

    const handleInstallClick = async () => {
        if (!installPrompt) return;
        await installPrompt.prompt();
        const choice = await installPrompt.userChoice;
        if (choice.outcome === 'accepted') {
            setInstallPrompt(null);
        }
    };

    if (!installPrompt || dismissed) {
        return null;
    }

    return (
        <section
            aria-label={t('Install KapitBayan App')}
            className="border-b border-slate-700 bg-slate-900 px-4 py-2.5 text-white sm:px-6"
        >
            <div className="mx-auto flex max-w-7xl items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-primary">
                        <Download className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <p className="text-xs sm:text-sm font-medium">
                        <strong className="font-semibold text-white">KapitBayan PWA:</strong>{' '}
                        {t('Install as an app on your phone or desktop for quick access and offline caching.')}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={handleInstallClick}
                        className="rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-white shadow-sm hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary cursor-pointer"
                    >
                        {t('Install')}
                    </button>
                    <button
                        type="button"
                        onClick={() => setDismissed(true)}
                        className="rounded-lg p-1.5 text-slate-400 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-white cursor-pointer"
                        aria-label={t('Dismiss install prompt')}
                    >
                        <X className="h-4 w-4" aria-hidden="true" />
                    </button>
                </div>
            </div>
        </section>
    );
};
