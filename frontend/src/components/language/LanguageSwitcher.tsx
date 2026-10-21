import { useLanguage } from '../../context/language-context';

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
    const { language, setLanguage, t } = useLanguage();

    return (
        <div className="inline-flex items-center gap-1.5 text-xs font-semibold">
            {!compact && <span>{t('Language')}</span>}
            <div role="group" aria-label={t('Choose language')} className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5">
                <button
                    type="button"
                    aria-pressed={language === 'en'}
                    onClick={() => setLanguage('en')}
                    className={`min-h-9 rounded-md px-2 text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 ${language === 'en' ? 'bg-primary/10 font-bold' : 'hover:bg-slate-100'}`}
                >
                    {compact ? 'EN' : t('English')}
                </button>
                <button
                    type="button"
                    aria-pressed={language === 'fil'}
                    onClick={() => setLanguage('fil')}
                    className={`min-h-9 rounded-md px-2 text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 ${language === 'fil' ? 'bg-primary/10 font-bold' : 'hover:bg-slate-100'}`}
                >
                    {compact ? 'FIL' : t('Filipino (Tagalog)')}
                </button>
            </div>
        </div>
    );
}
