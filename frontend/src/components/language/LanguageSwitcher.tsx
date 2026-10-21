import { useLanguage } from '../../context/language-context';

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
    const { language, setLanguage, t } = useLanguage();

    return (
        <label className="inline-flex items-center gap-1.5 text-xs font-semibold">
            {!compact && <span>{t('Language')}</span>}
            <select
                aria-label={t('Choose language')}
                value={language}
                onChange={(event) => setLanguage(event.target.value === 'fil' ? 'fil' : 'en')}
                className="min-h-10 rounded-lg border border-slate-300 bg-white px-2 text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
            >
                <option value="en">English</option>
                <option value="fil">{t('Filipino (Tagalog)')}</option>
            </select>
        </label>
    );
}
