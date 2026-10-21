import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { CheckCircle2, Clock3, FileHeart, Loader2, Send, XCircle } from 'lucide-react';
import { axiosPrivate } from '../../api/axios';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { useAuth } from '../../context/auth-context';
import { useLanguage } from '../../context/language-context';

interface AidRequest {
    id: number;
    requester_name: string;
    assistance_type: string;
    reason: string;
    status: 'PENDING' | 'UNDER_REVIEW' | 'APPROVED' | 'DECLINED';
    staff_notes: string;
    created_at: string;
}

const assistanceTypes = [
    'Medical assistance',
    'Food assistance',
    'Educational assistance',
    'Emergency assistance',
    'Other barangay assistance',
];

const statusLabel: Record<AidRequest['status'], string> = {
    PENDING: 'Pending review',
    UNDER_REVIEW: 'Under review',
    APPROVED: 'Approved',
    DECLINED: 'Declined',
};

export const AidRequests: React.FC = () => {
    const { user } = useAuth();
    const isStaff = user?.role === 'ADMIN';
    const { t } = useLanguage();
    const residentText = (source: string) => isStaff ? source : t(source);
    const [requests, setRequests] = useState<AidRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [retrying, setRetrying] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [reviewingId, setReviewingId] = useState<number | null>(null);
    const [assistanceType, setAssistanceType] = useState(assistanceTypes[0]);
    const [reason, setReason] = useState('');
    const [notes, setNotes] = useState<Record<number, string>>({});

    const loadRequests = async (isRetry = false) => {
        if (isRetry) setRetrying(true);
        try {
            const response = await axiosPrivate.get('/aid-requests/');
            const data = response.data.results || response.data;
            setRequests(Array.isArray(data) ? data : []);
            setLoadError(false);
        } catch {
            setLoadError(true);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    };

    useEffect(() => {
        void loadRequests();
    }, []);

    const submitRequest = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!reason.trim()) return;
        setSubmitting(true);
        try {
            await axiosPrivate.post('/aid-requests/', {
                assistance_type: assistanceType,
                reason: reason.trim(),
            });
            setReason('');
            toast.success(residentText('Assistance request submitted for staff review.'));
            await loadRequests();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Could not submit your request.');
        } finally {
            setSubmitting(false);
        }
    };

    const reviewRequest = async (
        request: AidRequest,
        status: AidRequest['status'],
    ) => {
        const staffNotes = notes[request.id]?.trim() || '';
        if (status === 'DECLINED' && !staffNotes) {
            toast.error(residentText('Add a reason before declining this request.'));
            return;
        }
        setReviewingId(request.id);
        try {
            const response = await axiosPrivate.patch(`/aid-requests/${request.id}/`, {
                status,
                staff_notes: staffNotes,
            });
            setRequests((current) => current.map((item) =>
                item.id === request.id ? response.data : item,
            ));
            toast.success(residentText(`Request marked ${statusLabel[status].toLowerCase()}.`));
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Could not update this request.');
        } finally {
            setReviewingId(null);
        }
    };

    return (
        <section className="space-y-6">
            <header className="rounded-2xl border border-slate-200 bg-white p-6">
                <div className="flex items-start gap-3">
                    <FileHeart className="mt-1 h-6 w-6 text-primary-text" />
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900">
                            {residentText(isStaff ? 'Barangay Assistance Requests' : 'Request Barangay Assistance')}
                        </h1>
                        <p className="mt-1 max-w-3xl text-sm text-slate-600">
                            {residentText(isStaff
                                ? 'Review requests for your barangay and record the decision and any resident-facing note.'
                                : 'Submit a request for manual review by barangay staff. Submission does not guarantee approval; the barangay will assess it under its own process.')}
                        </p>
                    </div>
                </div>
            </header>

            {!isStaff && (
                <form onSubmit={submitRequest} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6">
                    <h2 className="font-semibold text-slate-900">{residentText('New assistance request')}</h2>
                    <label className="block text-sm font-medium text-slate-700">
                        {residentText('Type of assistance')}
                        <select
                            value={assistanceType}
                            onChange={(event) => setAssistanceType(event.target.value)}
                            className="mt-1 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5"
                        >
                            {assistanceTypes.map((type) => <option key={type}>{residentText(type)}</option>)}
                        </select>
                    </label>
                    <label className="block text-sm font-medium text-slate-700">
                        {residentText('Reason for request')}
                        <textarea
                            required
                            maxLength={2000}
                            rows={4}
                            value={reason}
                            onChange={(event) => setReason(event.target.value)}
                            className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5"
                            placeholder={residentText('Describe the assistance you are requesting. Do not include passwords or unrelated sensitive details.')}
                        />
                    </label>
                    <button
                        type="submit"
                        disabled={submitting}
                        className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
                    >
                        {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                        {residentText('Submit for review')}
                    </button>
                </form>
            )}

            <div className="space-y-4">
                <h2 className="font-semibold text-slate-900">{residentText(isStaff ? 'Requests for your barangay' : 'Your requests')}</h2>
                {loading ? (
                    <div className="flex items-center gap-2 rounded-xl bg-white p-6 text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin" /> {residentText('Loading requests…')}
                    </div>
                ) : loadError ? (
                    <InlineErrorState
                        message={residentText("We couldn't load assistance requests.")}
                        onRetry={() => void loadRequests(true)}
                        retrying={retrying}
                    />
                ) : requests.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
                        {residentText('No assistance requests have been submitted.')}
                    </div>
                ) : requests.map((request) => {
                    const isOpen = request.status === 'PENDING' || request.status === 'UNDER_REVIEW';
                    return (
                        <article key={request.id} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                    <h3 className="font-semibold text-slate-900">{request.assistance_type}</h3>
                                    <p className="mt-1 text-xs text-slate-500">
                                        {isStaff ? `${request.requester_name} · ` : ''}
                                        {new Date(request.created_at).toLocaleDateString()}
                                    </p>
                                </div>
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                                    {request.status === 'APPROVED' ? <CheckCircle2 className="h-3.5 w-3.5" /> : request.status === 'DECLINED' ? <XCircle className="h-3.5 w-3.5" /> : <Clock3 className="h-3.5 w-3.5" />}
                                    {residentText(statusLabel[request.status])}
                                </span>
                            </div>
                            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{request.reason}</p>
                            {request.staff_notes && (
                                <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                                    <span className="font-semibold">{residentText('Staff note: ')}</span>{request.staff_notes}
                                </p>
                            )}
                            {isStaff && isOpen && (
                                <div className="space-y-3 border-t border-slate-100 pt-4">
                                    <label className="block text-sm font-medium text-slate-700">
                                        Review note
                                        <textarea
                                            rows={2}
                                            maxLength={2000}
                                            value={notes[request.id] ?? request.staff_notes}
                                            onChange={(event) => setNotes((current) => ({ ...current, [request.id]: event.target.value }))}
                                            className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2"
                                            placeholder="Add resident-facing information; a reason is required to decline."
                                        />
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        {request.status === 'PENDING' && (
                                            <button disabled={reviewingId === request.id} onClick={() => void reviewRequest(request, 'UNDER_REVIEW')} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium disabled:opacity-50">Start review</button>
                                        )}
                                        <button disabled={reviewingId === request.id} onClick={() => void reviewRequest(request, 'APPROVED')} className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Approve</button>
                                        <button disabled={reviewingId === request.id} onClick={() => void reviewRequest(request, 'DECLINED')} className="rounded-lg bg-rose-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Decline</button>
                                    </div>
                                </div>
                            )}
                        </article>
                    );
                })}
            </div>
        </section>
    );
};
