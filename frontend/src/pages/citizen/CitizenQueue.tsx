import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { axiosPrivate } from '../../api/axios';
import { getSafeApiErrorMessage } from '../../api/error-message';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { DigitalQueueTicketModal } from '../../components/queue/DigitalQueueTicketModal';
import {  
    Clock, 
    Users, 
    Ticket, 
    CheckCircle2,
    Plus, 
    Loader2, 
    Volume2,
    LogOut,
} from 'lucide-react';
import { useLanguage } from '../../context/language-context';

interface LiveStatus {
    current_ticket: string | null;
    total_waiting: number;
    avg_wait_mins: number;
}

interface UserTicket {
    id: number;
    ticket_id?: number;
    ticket_number: string;
    service_type: string;
    document_request_id?: number | null;
    document_request_type?: string | null;
    status: string;
    is_priority: boolean;
    created_at: string;
}

const SERVICE_TYPES = [
    'Document Processing & Clearances',
    'Barangay ID Application',
    'Certificate of Indigency',
    'General Inquiries & Complaints',
];

export const CitizenQueue: React.FC = () => {
    const { t } = useLanguage();
    const [liveStatus, setLiveStatus] = useState<LiveStatus>({
        current_ticket: null,
        total_waiting: 0,
        avg_wait_mins: 0,
    });
    const [activeTicket, setActiveTicket] = useState<UserTicket | null>(null);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [cancelling, setCancelling] = useState(false);

    // Form State
    const [serviceType, setServiceType] = useState(SERVICE_TYPES[0]);

    const fetchQueueData = async (showLoading = false) => {
        if (showLoading) setLoading(true);
        try {
            const [statusRes, ticketsRes] = await Promise.all([
                axiosPrivate.get('/tickets/live-status/'),
                axiosPrivate.get('/tickets/'),
            ]);
            const list = ticketsRes.data.results || ticketsRes.data || [];
            const current = list.find((t: UserTicket) => ['WAITING', 'SERVING'].includes(t.status.toUpperCase()));
            const ticketId = current?.ticket_id ?? current?.id;
            if (current && typeof ticketId !== 'number') {
                throw new Error('Queue ticket response is missing its identifier.');
            }
            setLiveStatus(statusRes.data);
            setActiveTicket(current ? { ...current, id: ticketId } : null);
            setLoadError(false);
        } catch {
            setLoadError(true);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchQueueData(true);
        // Auto-poll live queue status every 5 seconds
        const interval = setInterval(fetchQueueData, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleTakeTicket = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setSubmitting(true);
            const res = await axiosPrivate.post('/tickets/', {
                service_type: serviceType,
            });
            toast.success(`${t('Ticket generated!')} ${res.data.ticket_number}`);
            setIsModalOpen(false);
            fetchQueueData();
        } catch (err) {
            toast.error(getSafeApiErrorMessage(
                err,
                t("We couldn't create your queue ticket. Check your connection and try again."),
            ));
        } finally {
            setSubmitting(false);
        }
    };

    const handleCancelTicket = async (id: number) => {
        if (!Number.isSafeInteger(id) || id < 1) {
            toast.error(t("We couldn't identify your queue ticket. Refresh and try again."));
            return;
        }

        if (!window.confirm(t('Are you sure you want to cancel your queue ticket and leave the line?'))) {
            return;
        }

        try {
            setCancelling(true);
            await axiosPrivate.post(`/tickets/${id}/cancel/`);
            setActiveTicket(null);
            toast.success(t('You have left the queue.'));
            fetchQueueData();
        } catch (err) {
            toast.error(getSafeApiErrorMessage(
                err,
                t("We couldn't cancel your queue ticket. Check your connection and try again."),
            ));
        } finally {
            setCancelling(false);
        }
    };

    return (
        <div className="space-y-8">
            {/* Header Banner */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                        {t('Live Service Queue')}
                    </h1>
                    <p className="text-sm text-slate-500 mt-1">
                        {t('Real-time lobby ticker and digital queuing for barangay hall physical counters.')}
                    </p>
                </div>
                {!loading && !loadError && !activeTicket && (
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-primary-foreground text-sm font-semibold shadow-xs transition-all cursor-pointer shrink-0"
                    >
                        <Plus className="w-4 h-4" />
                        <span>{t('Get Queue Ticket')}</span>
                    </button>
                )}
            </div>

            {/* Live Counter Dashboard Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Now Serving */}
                <div className="bg-gradient-to-br from-primary to-primary-hover rounded-2xl p-6 text-primary-foreground shadow-md relative overflow-hidden">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-primary-foreground uppercase tracking-wider">
                            {t('Now Serving')}
                        </span>
                        <span className="flex items-center gap-1 text-[11px] text-primary-foreground font-bold bg-emerald-400/10 px-2 py-0.5 rounded-full border border-emerald-400/20">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                            {t('Live Counter')}
                        </span>
                    </div>
                    <div className="mt-4 text-4xl sm:text-5xl font-black tracking-tight text-primary-foreground font-mono">
                        {loadError ? '—' : liveStatus.current_ticket || '—'}
                    </div>
                    <p className="text-xs text-primary-foreground opacity-80 mt-2 flex items-center gap-1.5">
                        <Volume2 className="w-3.5 h-3.5 text-primary-foreground" />
                        {t('Counter 1 - Public Assistance Desk')}
                    </p>
                </div>

                {/* Total Waiting in Line */}
                <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col justify-between">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                            {t('Residents Waiting')}
                        </span>
                        <div className="w-8 h-8 rounded-xl bg-sky-50 text-primary-text flex items-center justify-center">
                            <Users className="w-4 h-4" />
                        </div>
                    </div>
                    <div className="mt-4 text-3xl font-extrabold text-slate-900">
                        {loadError ? '—' : liveStatus.total_waiting}
                    </div>
                    <p className="text-xs text-slate-500 mt-2">
                        {t('In active queue line')}
                    </p>
                </div>

                {/* Estimated Wait Time */}
                <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col justify-between">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                            {t('Estimated Wait')}
                        </span>
                        <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                            <Clock className="w-4 h-4" />
                        </div>
                    </div>
                    <div className="mt-4 text-3xl font-extrabold text-slate-900">
                        {loadError ? '—' : <>~{liveStatus.avg_wait_mins} <span className="text-base font-normal text-slate-500">{t('mins')}</span></>}
                    </div>
                    <p className="text-xs text-slate-500 mt-2">
                        {t('Based on current service pace')}
                    </p>
                </div>
            </div>

            {/* Resident Active Ticket Card */}
            {loading ? (
                <div className="bg-white rounded-2xl p-8 border border-slate-200 text-center flex items-center justify-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin text-primary-text mr-2" />
                    <span>{t('Synchronizing your queue ticket...')}</span>
                </div>
            ) : loadError ? (
                <InlineErrorState
                    message={t("We couldn't load your queue details.")}
                    onRetry={() => void fetchQueueData(true)}
                    retrying={loading}
                />
            ) : activeTicket ? (
                <div className={`rounded-2xl p-6 sm:p-8 border shadow-sm transition-all ${
                    activeTicket.status.toUpperCase() === 'SERVING'
                        ? 'bg-emerald-50/80 border-emerald-300 ring-2 ring-emerald-500/20'
                        : 'bg-white border-slate-200'
                }`}>
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                        <div className="flex items-center gap-5">
                            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center font-black text-2xl shadow-sm ${
                                activeTicket.status.toUpperCase() === 'SERVING'
                                    ? 'bg-emerald-600 text-white'
                                    : 'bg-primary text-primary-foreground'
                            }`}>
                                {activeTicket.ticket_number}
                            </div>
                            <div>
                                <div className="flex items-center gap-2">
                                    <h3 className="text-lg font-bold text-slate-900">
                                        {t('Your Active Queue Ticket')}
                                    </h3>
                                    {activeTicket.is_priority && (
                                        <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-amber-100 text-amber-800 border border-amber-200">
                                            {t('Priority Lane')}
                                        </span>
                                    )}
                                </div>
                                <p className="text-xs text-slate-500 mt-1">
                                    {t('Service')}: <span className="font-semibold text-slate-700 break-words">{t(activeTicket.service_type)}</span>
                                </p>
                                {activeTicket.document_request_id && (
                                    <p className="text-xs text-blue-700 mt-1">
                                        {t('Linked document request')} #{activeTicket.document_request_id}
                                    </p>
                                )}
                                <p className="text-[11px] text-slate-400 mt-0.5">
                                    {t('Issued')}: {new Date(activeTicket.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </p>
                            </div>
                        </div>

                        <div className="w-full md:w-auto flex flex-col sm:flex-row items-start sm:items-center gap-3">
                            {activeTicket.status.toUpperCase() === 'SERVING' ? (
                                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 text-white font-bold text-xs shadow-sm">
                                    <CheckCircle2 className="w-4 h-4" />
                                    <span>{t('Now Being Served! Proceed to Counter')}</span>
                                </div>
                                                        ) : (
                                <div className="flex items-center gap-2">
                                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-50 text-amber-700 border border-amber-200 text-xs font-semibold">
                                        <Clock className="w-4 h-4" />
                                        <span>{t('Waiting for your turn')}</span>
                                    </div>
                                    <button
                                        onClick={() => handleCancelTicket(activeTicket.id)}
                                        disabled={cancelling}
                                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 text-xs font-bold transition-all cursor-pointer"
                                        aria-label={t('Leave queue and cancel ticket')}
                                    >
                                        {cancelling ? (
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                        ) : (
                                            <LogOut className="w-3.5 h-3.5" />
                                        )}
                                        <span>{t('Leave Queue')}</span>
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            ) : (
                <div className="bg-white rounded-2xl p-8 border border-slate-200 text-center flex flex-col items-center justify-center">
                    <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-400 flex items-center justify-center mb-3">
                        <Ticket className="w-6 h-6" />
                    </div>
                    <h3 className="text-base font-bold text-slate-900">{t('You do not have an active queue ticket')}</h3>
                    <p className="text-sm text-slate-500 max-w-md mt-1">
                        {t('Planning to visit the barangay hall? Take a digital queue number in advance to reserve your position in line.')}
                    </p>
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="mt-4 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary-hover transition-all cursor-pointer"
                    >
                        {t('Get a Ticket Now')}
                    </button>
                </div>
            )}

            {/* Take Ticket Modal */}
            {isModalOpen && (
                <DigitalQueueTicketModal
                    onClose={() => setIsModalOpen(false)}
                    onSubmit={handleTakeTicket}
                    serviceType={serviceType}
                    setServiceType={setServiceType}
                    serviceTypes={SERVICE_TYPES}
                    submitting={submitting}
                />
            )}
        </div>
    );
};
