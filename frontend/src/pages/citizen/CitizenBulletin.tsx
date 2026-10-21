import React, { useState, useEffect, useCallback } from "react";
import { axiosPrivate } from "../../api/axios";
import { InlineErrorState } from "../../components/ui/InlineErrorState";
import { useLanguage } from "../../context/language-context";
import { 
        Radio,
        Pin,
        Calendar, 
        MapPin, 
        Clock, 
        Loader2, 
        Megaphone,
        CalendarCheck2
 } from "lucide-react";

interface Announcement {
        id: number
        title: string
        content: string
        is_pinned: boolean
        created_at: string
}

interface Activity {
        id: number
        title: string
        description: string
        location: string
        event_datetime: string
        created_at: string
}

export const CitizenBulletin: React.FC = () => {
        const { t } = useLanguage();
        const [activeTab, setActiveTab] = useState<'announcements' | 'activities'>('announcements')
        const [announcements, setAnnouncements] = useState<Announcement[]>([])
        const [activities, setActivities] = useState<Activity[]>([])
        const [loading, setLoading] = useState(true)
        const [loadErrors, setLoadErrors] = useState({ announcements: false, activities: false })

        const fetchData = useCallback(async () => {
                setLoading(true)
                try {
                        const [annRes, actRes] = await Promise.allSettled([
                                axiosPrivate.get('/announcements/'),
                                axiosPrivate.get('/activities/'),
                        ])
                        setLoadErrors({
                                announcements: annRes.status === 'rejected',
                                activities: actRes.status === 'rejected',
                        })
                        if (annRes.status === 'fulfilled') {
                                const responseData = annRes.value.data.results || annRes.value.data || []
                                const data = Array.isArray(responseData) ? responseData : []
                                setAnnouncements(
                                        [...data].sort((a, b) => (b.is_pinned ? 1 : 0) - (a.is_pinned ? 1 : 0))
                                )
                        }

                        if (actRes.status === 'fulfilled') {
                                const responseData = actRes.value.data.results || actRes.value.data || []
                                setActivities(Array.isArray(responseData) ? responseData : [])
                        }
                } finally {
                        setLoading(false)
                }
        }, [])

        useEffect(() => {
                void fetchData()
        }, [fetchData])
        
return (
        <div className="space-y-6">
            {/* Header Banner */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                        {t('Community Bulletin Board')}
                    </h1>
                    <p className="text-sm text-slate-500 mt-1">
                        {t('Official barangay council announcements, public health advisories, and community programs.')}
                    </p>
                </div>
                {/* Tab Switcher */}
                <div className="flex bg-[#F1F5F9] p-1.5 rounded-xl border border-slate-200 shrink-0">
                    <button
                        onClick={() => setActiveTab('announcements')}
                        aria-pressed={activeTab === 'announcements'}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                            activeTab === 'announcements'
                                ? 'bg-white text-primary-text shadow-xs'
                                : 'text-slate-600 hover:text-slate-900'
                        }`}
                    >
                        <Megaphone className="w-3.5 h-3.5" />
                        <span>{t('Announcements')} ({announcements.length})</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('activities')}
                        aria-pressed={activeTab === 'activities'}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                            activeTab === 'activities'
                                ? 'bg-white text-primary-text shadow-xs'
                                : 'text-slate-600 hover:text-slate-900'
                        }`}
                    >
                        <Calendar className="w-3.5 h-3.5" />
                        <span>{t('Activities')} ({activities.length})</span>
                    </button>
                </div>
            </div>
            {loading ? (
                <div className="bg-white rounded-2xl p-12 border border-slate-200 text-center flex flex-col items-center justify-center text-slate-400">
                    <Loader2 className="w-8 h-8 animate-spin text-primary-text mb-2" />
                    <p className="text-sm">{t('Retrieving bulletin notices...')}</p>
                </div>
            ) : loadErrors[activeTab] ? (
                <InlineErrorState
                    message={activeTab === 'announcements' ? t("We couldn't load announcements.") : t("We couldn't load activities.")}
                    onRetry={() => void fetchData()}
                    retrying={loading}
                />
            ) : activeTab === 'announcements' ? (
                /* Announcements Feed */
                announcements.length === 0 ? (
                    <div className="bg-white rounded-2xl p-12 border border-slate-200 text-center flex flex-col items-center justify-center">
                        <Radio className="w-10 h-10 text-slate-300 mb-2" />
                        <h3 className="text-base font-bold text-slate-900">No announcements posted</h3>
                        <p className="text-sm text-slate-500 mt-1">There are no active public notices from the barangay hall at this time.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {announcements.map((item) => (
                            <div
                                key={item.id}
                                className={`bg-white rounded-2xl p-6 border shadow-xs transition-all flex flex-col justify-between ${
                                    item.is_pinned
                                        ? 'border-primary ring-2 ring-primary/10'
                                        : 'border-slate-200'
                                }`}
                            >
                                <div>
                                    <div className="flex items-center justify-between gap-2 mb-3">
                                        <span className="text-xs font-semibold text-slate-400">
                                            {new Date(item.created_at).toLocaleDateString(undefined, {
                                                year: 'numeric',
                                                month: 'short',
                                                day: 'numeric',
                                            })}
                                        </span>
                                        {item.is_pinned && (
                                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-sky-50 text-primary-text border border-sky-200">
                                                <Pin className="w-3 h-3" /> Pinned Notice
                                            </span>
                                        )}
                                    </div>
                                    <h3 className="text-lg font-bold text-slate-900 mb-2 leading-snug">
                                        {item.title}
                                    </h3>
                                    <p className="text-sm text-slate-600 whitespace-pre-line leading-relaxed">
                                        {item.content}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )
            ) : (
                /* Community Activities Feed */
                activities.length === 0 ? (
                    <div className="bg-white rounded-2xl p-12 border border-slate-200 text-center flex flex-col items-center justify-center">
                        <CalendarCheck2 className="w-10 h-10 text-slate-300 mb-2" />
                        <h3 className="text-base font-bold text-slate-900">No scheduled activities</h3>
                        <p className="text-sm text-slate-500 mt-1">There are no upcoming barangay events scheduled on the calendar.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {activities.map((act) => (
                            <div
                                key={act.id}
                                className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col justify-between"
                            >
                                <div>
                                    <div className="w-10 h-10 rounded-xl bg-sky-50 text-primary-text flex items-center justify-center mb-4">
                                        <Calendar className="w-5 h-5" />
                                    </div>
                                    <h3 className="text-base font-bold text-slate-900 mb-2">
                                        {act.title}
                                    </h3>
                                    <p className="text-xs text-slate-600 mb-4 line-clamp-3 leading-relaxed">
                                        {act.description}
                                    </p>
                                </div>
                                <div className="pt-4 border-t border-slate-100 space-y-2 text-xs text-slate-500">
                                    <div className="flex items-center gap-2">
                                        <Clock className="w-3.5 h-3.5 text-primary-text shrink-0" />
                                        <span>
                                            {new Date(act.event_datetime).toLocaleString(undefined, {
                                                dateStyle: 'medium',
                                                timeStyle: 'short',
                                            })}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <MapPin className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                                        <span className="truncate">{act.location}</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )
            )}
        </div>
    );
}
