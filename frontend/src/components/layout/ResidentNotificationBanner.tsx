import { useCallback, useEffect, useState } from 'react';
import { BellRing, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { axiosPrivate } from '../../api/axios';
import { useLanguage } from '../../context/language-context';

interface ResidentNotification {
    id: number;
    notification_type: string;
    title: string;
    message: string;
    is_read: boolean;
}

export function ResidentNotificationBanner() {
    const { t } = useLanguage();
    const navigate = useNavigate();
    const [notification, setNotification] = useState<ResidentNotification | null>(null);

    const loadLatestUnread = useCallback(async () => {
        try {
            const response = await axiosPrivate.get('/resident-notifications/');
            const rows = Array.isArray(response.data) ? response.data : response.data?.results;
            if (!Array.isArray(rows)) return;
            const latest = rows.find((item): item is ResidentNotification =>
                typeof item?.id === 'number'
                && typeof item?.title === 'string'
                && typeof item?.message === 'string'
                && item.is_read === false,
            );
            setNotification(latest ?? null);
        } catch {
            // Keep the portal usable if notifications are temporarily unavailable.
        }
    }, []);

    useEffect(() => {
        void loadLatestUnread();
        const interval = window.setInterval(() => {
            if (document.visibilityState === 'visible') void loadLatestUnread();
        }, 15_000);
        const handleVisibility = () => {
            if (document.visibilityState === 'visible') void loadLatestUnread();
        };
        document.addEventListener('visibilitychange', handleVisibility);
        return () => {
            window.clearInterval(interval);
            document.removeEventListener('visibilitychange', handleVisibility);
        };
    }, [loadLatestUnread]);

    const markAsRead = async () => {
        if (!notification) return;
        try {
            await axiosPrivate.patch(`/resident-notifications/${notification.id}/`, { is_read: true });
            await loadLatestUnread();
        } catch {
            // Leave the notice visible so the resident can retry later.
        }
    };

    if (!notification) return null;

    const destination = notification.notification_type === 'queue'
        ? '/portal/queue'
        : '/portal/documents';

    return (
        <section
            role="status"
            aria-live="polite"
            aria-label={t('New notification')}
            className="mb-6 flex flex-col gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 shadow-sm sm:flex-row sm:items-center"
        >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-800">
                <BellRing className="h-5 w-5" aria-hidden="true" />
            </span>
            <div className="min-w-0 flex-1">
                <h2 className="font-bold text-blue-950">{t(notification.title)}</h2>
                <p className="mt-1 text-sm text-blue-900">{t(notification.message)}</p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
                <button
                    type="button"
                    onClick={() => navigate(destination)}
                    className="min-h-11 rounded-lg bg-blue-800 px-4 text-sm font-bold text-white hover:bg-blue-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-800 focus-visible:ring-offset-2"
                >
                    {t('View update')}
                </button>
                <button
                    type="button"
                    onClick={() => void markAsRead()}
                    aria-label={t('Mark notification as read')}
                    className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-blue-300 bg-white px-3 text-sm font-semibold text-blue-900 hover:bg-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-800"
                >
                    <Check className="h-4 w-4" aria-hidden="true" />
                    {t('Dismiss')}
                </button>
            </div>
        </section>
    );
}
