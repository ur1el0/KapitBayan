import { useCallback, useEffect, useState } from 'react';
import { Check, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { axiosPrivate } from '../../api/axios';
import { InlineErrorState } from '../../components/ui/InlineErrorState';

interface TransferRequest {
    id: number;
    resident_name: string;
    resident_username: string;
    source_barangay_name: string;
    destination_barangay_name: string;
    reason: string;
    status: 'PENDING' | 'APPROVED' | 'REJECTED';
    review_note: string;
    created_at: string;
    reviewed_at: string | null;
}

const responseRows = (data: unknown): TransferRequest[] => {
    const rows = Array.isArray(data) ? data : (data as { results?: unknown[] } | null)?.results;
    return Array.isArray(rows) ? rows as TransferRequest[] : [];
};

export function ResidentTransfers() {
    const [requests, setRequests] = useState<TransferRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [confirmed, setConfirmed] = useState<Record<number, boolean>>({});
    const [rejectionNotes, setRejectionNotes] = useState<Record<number, string>>({});
    const [busyId, setBusyId] = useState<number | null>(null);
    const [actionError, setActionError] = useState<string | null>(null);

    const loadRequests = useCallback(async (retry = false) => {
        setRefreshing(retry);
        try {
            const response = await axiosPrivate.get('/auth/resident-transfers/');
            setRequests(responseRows(response.data));
            setLoadError(false);
        } catch {
            setLoadError(true);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        void loadRequests();
    }, [loadRequests]);

    const review = async (request: TransferRequest, decision: 'approve' | 'reject') => {
        const note = rejectionNotes[request.id]?.trim() ?? '';
        if (decision === 'approve' && !confirmed[request.id]) return;
        if (decision === 'reject' && !note) {
            setActionError(`Enter a reason before rejecting ${request.resident_name}'s transfer.`);
            return;
        }
        setBusyId(request.id);
        setActionError(null);
        try {
            await axiosPrivate.post(`/auth/resident-transfers/${request.id}/${decision}/`, decision === 'approve'
                ? { residency_confirmed: true }
                : { review_note: note });
            await loadRequests();
        } catch {
            setActionError(`Could not ${decision} this request. Refresh and try again.`);
        } finally {
            setBusyId(null);
        }
    };

    if (loading) return <p role="status" className="p-5 text-sm text-slate-600">Loading transfer requests…</p>;
    if (loadError && requests.length === 0) {
        return <InlineErrorState message="We couldn't load resident transfer requests." onRetry={() => void loadRequests(true)} retrying={refreshing} />;
    }

    return (
        <section className="space-y-4" aria-labelledby="resident-transfers-heading">
            <header className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4">
                <div className="flex gap-3">
                    <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-blue-800" aria-hidden="true" />
                    <div>
                        <h3 id="resident-transfers-heading" className="font-bold text-blue-950">Resident Barangay transfer requests</h3>
                        <p className="mt-1 text-sm text-blue-900">Approve only after independently verifying the resident’s identity and residence through an official channel. Existing requests and tickets remain with their original Barangay.</p>
                    </div>
                </div>
                <button type="button" onClick={() => void loadRequests(true)} disabled={refreshing} className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-blue-300 bg-white px-3 text-sm font-semibold text-blue-900 disabled:opacity-60">
                    <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} aria-hidden="true" /> Refresh
                </button>
            </header>

            {actionError && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{actionError}</p>}
            {requests.length === 0 ? (
                <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">No transfer requests have been submitted to this Barangay.</div>
            ) : requests.map((request) => (
                <article key={request.id} className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h4 className="text-base font-bold text-slate-900">{request.resident_name}</h4>
                            <p className="text-sm text-slate-600">Account: {request.resident_username}</p>
                            <p className="mt-1 text-sm text-slate-700">{request.source_barangay_name} → {request.destination_barangay_name}</p>
                        </div>
                        <span className={`rounded-full px-3 py-1 text-xs font-bold ${request.status === 'PENDING' ? 'bg-amber-100 text-amber-900' : request.status === 'APPROVED' ? 'bg-emerald-100 text-emerald-900' : 'bg-rose-100 text-rose-900'}`}>
                            {request.status.replace('_', ' ')}
                        </span>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700"><strong>Resident’s reason:</strong> {request.reason}</div>
                    {request.status === 'PENDING' ? (
                        <div className="grid gap-4 border-t border-slate-100 pt-4 lg:grid-cols-2">
                            <div className="space-y-3">
                                <label className="flex items-start gap-3 text-sm leading-5 text-slate-700">
                                    <input type="checkbox" checked={Boolean(confirmed[request.id])} onChange={(event) => setConfirmed((current) => ({ ...current, [request.id]: event.target.checked }))} className="mt-1 h-4 w-4 accent-primary" />
                                    <span>I independently verified this resident’s identity and residence through an official channel.</span>
                                </label>
                                <button type="button" onClick={() => void review(request, 'approve')} disabled={!confirmed[request.id] || busyId === request.id} className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">
                                    <Check className="h-4 w-4" aria-hidden="true" /> Approve transfer
                                </button>
                            </div>
                            <div className="space-y-2">
                                <label htmlFor={`transfer-rejection-${request.id}`} className="block text-sm font-semibold text-slate-800">Rejection reason</label>
                                <textarea id={`transfer-rejection-${request.id}`} maxLength={500} value={rejectionNotes[request.id] ?? ''} onChange={(event) => setRejectionNotes((current) => ({ ...current, [request.id]: event.target.value }))} className="min-h-20 w-full rounded-lg border border-slate-300 p-3 text-sm" />
                                <button type="button" onClick={() => void review(request, 'reject')} disabled={busyId === request.id} className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-rose-300 px-4 text-sm font-bold text-rose-800 disabled:opacity-50">
                                    <X className="h-4 w-4" aria-hidden="true" /> Reject request
                                </button>
                            </div>
                        </div>
                    ) : request.review_note ? (
                        <p className="text-sm text-slate-600"><strong>Review note:</strong> {request.review_note}</p>
                    ) : null}
                </article>
            ))}
        </section>
    );
}
