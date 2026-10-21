import React, { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { Megaphone } from 'lucide-react';
import { axiosPublic } from '../../api/axios';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { LanguageSwitcher } from '../../components/language/LanguageSwitcher';
import { useLanguage } from '../../context/language-context';

interface PublicAnnouncement {
    id: number;
    title: string;
    content: string;
    is_pinned: boolean;
    created_at: string;
}

export const PublicAnnouncements: React.FC = () => {
    const { t } = useLanguage();
    const { barangayId } = useParams<{ barangayId: string }>();
    const { hash } = useLocation();
    const [announcements, setAnnouncements] = useState<PublicAnnouncement[]>([]);
    const [loading, setLoading] = useState(true);
    const [failed, setFailed] = useState(false);
    const [retrying, setRetrying] = useState(false);
    const [missingLinkedAnnouncement, setMissingLinkedAnnouncement] = useState(false);

    const loadAnnouncements = useCallback(async (isRetry = false) => {
        if (!barangayId) return;
        if (isRetry) setRetrying(true);
        try {
            const response = await axiosPublic.get(`/public/barangays/${barangayId}/announcements/`);
            setAnnouncements(response.data);
            setFailed(false);
        } catch {
            setFailed(true);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    }, [barangayId]);

    useEffect(() => {
        void loadAnnouncements();
    }, [loadAnnouncements]);

    useEffect(() => {
        const targetMatch = /^#announcement-(\d+)$/.exec(hash);
        if (loading || failed || !targetMatch) {
            setMissingLinkedAnnouncement(false);
            return;
        }

        const target = document.getElementById(`announcement-${targetMatch[1]}`);
        setMissingLinkedAnnouncement(!target);
        if (target) {
            target.focus({ preventScroll: true });
            target.scrollIntoView?.({ block: 'start' });
        }
    }, [announcements, failed, hash, loading]);

    return (
        <main className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900">
            <div className="mx-auto max-w-3xl space-y-6">
                <header className="rounded-2xl bg-primary p-6 text-primary-foreground">
                    <div className="mb-4 flex justify-end"><LanguageSwitcher compact /></div>
                    <div className="flex items-center gap-3">
                        <Megaphone aria-hidden="true" />
                        <div>
                            <p className="text-xs font-bold uppercase tracking-wider opacity-80">{t('KapitBayan Community Bulletin')}</p>
                            <h1 className="text-2xl font-bold">{t('Barangay announcements')}</h1>
                        </div>
                    </div>
                    <p className="mt-3 text-sm opacity-90">{t('Official information is shared here. Requests and transactions must be completed inside KapitBayan.')}</p>
                </header>
                {loading ? <p role="status">{t('Loading announcements…')}</p> : failed ? (
                    <InlineErrorState
                        message={t('Announcements are temporarily unavailable.')}
                        onRetry={() => { void loadAnnouncements(true); }}
                        retrying={retrying}
                    />
                ) : announcements.length === 0 ? (
                    <p className="rounded-xl bg-white p-6 text-slate-600">{t('There are no public announcements at this time.')}</p>
                ) : announcements.map((announcement) => (
                    <article
                        key={announcement.id}
                        id={`announcement-${announcement.id}`}
                        tabIndex={-1}
                        aria-labelledby={`announcement-title-${announcement.id}`}
                        className="scroll-mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                        {announcement.is_pinned && <p className="mb-2 text-xs font-bold uppercase text-amber-700">{t('Pinned announcement')}</p>}
                        <h2 id={`announcement-title-${announcement.id}`} className="text-xl font-bold">{announcement.title}</h2>
                        <p className="mt-2 text-xs text-slate-500">{new Date(announcement.created_at).toLocaleDateString()}</p>
                        <p className="mt-4 whitespace-pre-wrap leading-relaxed text-slate-700">{announcement.content}</p>
                    </article>
                ))}
                {missingLinkedAnnouncement && (
                    <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                        {t('This announcement is no longer available in the public bulletin.')}
                    </p>
                )}
                <footer className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">
                    {t('Need to file a request?')} <Link className="font-semibold text-primary-text underline" to="/login">{t('Sign in to KapitBayan')}</Link> {t('to complete the transaction.')}
                </footer>
            </div>
        </main>
    );
};
