import { useCallback, useEffect, useState } from 'react';
import { axiosPrivate } from '../../api/axios';
import { InlineErrorState } from '../../components/ui/InlineErrorState';

interface Application {
    id: number;
    application_type: 'BARANGAY' | 'OFFICIAL';
    name: string;
    municipality: string;
    province: string;
    applicant_name: string;
    applicant_position: string;
    applicant_email: string;
    applicant_phone: string;
    status: 'PENDING' | 'APPROVED' | 'REJECTED';
    review_note: string;
}

function resultsFrom(response: any): Application[] {
    return response.data.results || response.data;
}

export function BarangayApplications() {
    const [applications, setApplications] = useState<Application[]>([]);
    const [notes, setNotes] = useState<Record<number, string>>({});
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [retrying, setRetrying] = useState(false);
    const [error, setError] = useState('');
    const [savingId, setSavingId] = useState<number | null>(null);

    const loadApplications = useCallback(async (isRetry = false) => {
        if (isRetry) setRetrying(true);
        try {
            const response = await axiosPrivate.get('/auth/barangay-applications/');
            setApplications(resultsFrom(response));
            setLoadError(false);
        } catch {
            setLoadError(true);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    }, []);

    useEffect(() => { void loadApplications(); }, [loadApplications]);

    const review = async (application: Application, decision: 'APPROVED' | 'REJECTED') => {
        const reviewNote = notes[application.id]?.trim() || '';
        if (decision === 'APPROVED' && !window.confirm(`Approve the official account request for ${application.applicant_name} at ${application.name}?`)) return;
        if (decision === 'REJECTED' && !reviewNote) {
            setError('Enter a reason before rejecting an application.');
            return;
        }

        setSavingId(application.id);
        setError('');
        try {
            const response = await axiosPrivate.post(`/auth/barangay-applications/${application.id}/review/`, {
                status: decision,
                review_note: reviewNote,
            });
            setApplications((current) => current.map((item) => item.id === application.id ? response.data : item));
        } catch (requestError: any) {
            setError(requestError.response?.data?.detail || requestError.response?.data?.name?.[0] || 'Could not review this application.');
        } finally {
            setSavingId(null);
        }
    };

    return (
        <section className="mx-auto max-w-6xl space-y-5 p-4 sm:p-8">
            <header>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-text">DILG administration</p>
                <h1 className="mt-1 text-2xl font-extrabold text-slate-900">Official Account Applications</h1>
                <p className="mt-2 text-sm text-slate-600">Verify each official through official channels before approving. Approval provisions a passwordless account for the verified official.</p>
            </header>
            {error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
            {loading ? <p role="status" className="text-sm text-slate-500">Loading applications…</p> : loadError ? (
                <InlineErrorState
                    message="Could not load barangay applications."
                    onRetry={() => { void loadApplications(true); }}
                    retrying={retrying}
                />
            ) : applications.length === 0 ? (
                <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">No applications have been submitted.</p>
            ) : (
                <div className="space-y-4">
                    {applications.map((application) => (
                        <article key={application.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                    <h2 className="text-lg font-bold text-slate-900">{application.applicant_name} — Official Account Request</h2>
                                    <p className="text-sm text-slate-600">{application.name} ({application.municipality}, {application.province})</p>
                                </div>
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{application.status}</span>
                            </div>
                            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                                <div><dt className="font-semibold text-slate-500">Applicant</dt><dd className="break-words">{application.applicant_name} · {application.applicant_position}</dd></div>
                                <div><dt className="font-semibold text-slate-500">Official contact</dt><dd className="break-words">{application.applicant_email} · {application.applicant_phone}</dd></div>
                            </dl>
                            {application.status === 'PENDING' && (
                                <div className="mt-4 border-t border-slate-100 pt-4">
                                    <label className="block text-sm font-medium text-slate-700">Review note
                                        <textarea rows={2} maxLength={1000} value={notes[application.id] || ''} onChange={(event) => setNotes((current) => ({ ...current, [application.id]: event.target.value }))} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="Required for rejection; include the verification outcome." />
                                    </label>
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        <button type="button" onClick={() => void review(application, 'APPROVED')} disabled={savingId === application.id} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{savingId === application.id ? 'Saving…' : 'Approve official account'}</button>
                                        <button type="button" onClick={() => void review(application, 'REJECTED')} disabled={savingId === application.id || !notes[application.id]?.trim()} className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Reject</button>
                                    </div>
                                </div>
                            )}
                            {application.review_note && <p className="mt-3 text-sm text-slate-600">Review note: {application.review_note}</p>}
                        </article>
                    ))}
                </div>
            )}
        </section>
    );
}
