import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Building2, CheckCircle2, ClipboardCheck, LogOut, ShieldCheck, XCircle } from 'lucide-react';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { useAuth } from '../../context/auth-context';
import {
    approveBarangayApplication,
    downloadBarangayApplicationProof,
    fetchBarangayApplications,
    rejectBarangayApplication,
    type BarangayApplication,
    type BarangayApplicationStatus,
} from '../../api/barangayOnboarding';

function apiErrorMessage(error: unknown, fallback: string) {
    if (!error || typeof error !== 'object' || !('response' in error)) return fallback;
    const response = error as { response?: { data?: Record<string, unknown> } };
    const data = response.response?.data;
    if (!data || typeof data !== 'object') return fallback;
    if (typeof data.detail === 'string') return data.detail;
    for (const key of ['applicant_email', 'contact_verified', 'proof_reviewed', 'reason']) {
        const value = data[key];
        if (typeof value === 'string') return value;
        if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
    }
    return fallback;
}

function dateLabel(value: string) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function PlatformBarangayApplications() {
    const { logout, user } = useAuth();
    const [applications, setApplications] = useState<BarangayApplication[]>([]);
    const [count, setCount] = useState(0);
    const [filter, setFilter] = useState<BarangayApplicationStatus>('PENDING');
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [retrying, setRetrying] = useState(false);
    const [loadError, setLoadError] = useState(false);
    const [verified, setVerified] = useState<Record<number, boolean>>({});
    const [proofReviewed, setProofReviewed] = useState<Record<number, boolean>>({});
    const [proofDownloads, setProofDownloads] = useState<Record<number, { url: string; filename: string }>>({});
    const [proofLoadingId, setProofLoadingId] = useState<number | null>(null);
    const [approvalNotes, setApprovalNotes] = useState<Record<number, string>>({});
    const [rejectionReasons, setRejectionReasons] = useState<Record<number, string>>({});
    const [busyId, setBusyId] = useState<number | null>(null);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const proofDownloadUrls = useRef(new Map<number, string>());

    useEffect(() => () => {
        proofDownloadUrls.current.forEach((url) => URL.revokeObjectURL(url));
        proofDownloadUrls.current.clear();
    }, []);

    const loadApplications = useCallback(async (isRetry = false) => {
        if (isRetry) setRetrying(true);
        else setLoading(true);
        try {
            const result = await fetchBarangayApplications(filter, page);
            setApplications(Array.isArray(result.results) ? result.results : []);
            setCount(result.count);
            setLoadError(false);
        } catch {
            setLoadError(true);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    }, [filter, page]);

    useEffect(() => { void loadApplications(); }, [loadApplications]);

    const applyReview = async (application: BarangayApplication) => {
        if (!verified[application.id]) return;
        if (application.has_applicant_account && !proofReviewed[application.id]) return;
        if (!window.confirm(`Approve ${application.name}, ${application.municipality}, ${application.province} and activate the applicant's Admin account?`)) return;
        setBusyId(application.id);
        setMessage(null);
        try {
            const updated = await approveBarangayApplication(application.id, {
                contact_verified: true,
                proof_reviewed: application.has_applicant_account ? true : false,
                review_note: approvalNotes[application.id]?.trim() || '',
            });
            clearProofDownload(application.id);
            setApplications((current) => current.map((item) => item.id === updated.id ? updated : item).filter((item) => filter !== 'PENDING' || item.status === 'PENDING'));
            setCount((current) => filter === 'PENDING' ? Math.max(0, current - 1) : current);
            setMessage({
                type: 'success',
                text: updated.admin_can_sign_in
                    ? `Barangay approved. ${updated.created_admin_email} can now sign in with the official email and password set during the application.`
                    : `Historical application approved. A private password setup email was requested for ${updated.created_admin_email ?? updated.applicant_email}.`,
            });
        } catch (error) {
            setMessage({ type: 'error', text: apiErrorMessage(error, 'Could not approve this application.') });
        } finally {
            setBusyId(null);
        }
    };

    const prepareProofDownload = async (application: BarangayApplication) => {
        setProofLoadingId(application.id);
        setMessage(null);
        try {
            const download = await downloadBarangayApplicationProof(application.id);
            const previousUrl = proofDownloadUrls.current.get(application.id);
            if (previousUrl) URL.revokeObjectURL(previousUrl);
            proofDownloadUrls.current.set(application.id, download.url);
            setProofDownloads((current) => ({ ...current, [application.id]: download }));
        } catch (error) {
            setMessage({ type: 'error', text: apiErrorMessage(error, 'Could not securely retrieve this authority document.') });
        } finally {
            setProofLoadingId(null);
        }
    };

    const clearProofDownload = (applicationId: number) => {
        const url = proofDownloadUrls.current.get(applicationId);
        if (url) URL.revokeObjectURL(url);
        proofDownloadUrls.current.delete(applicationId);
        setProofDownloads((current) => {
            const remaining = { ...current };
            delete remaining[applicationId];
            return remaining;
        });
    };

    const reject = async (application: BarangayApplication) => {
        const reason = rejectionReasons[application.id]?.trim() ?? '';
        if (reason.length < 5) {
            setMessage({ type: 'error', text: 'Enter a rejection reason with at least five characters.' });
            return;
        }
        setBusyId(application.id);
        setMessage(null);
        try {
            const updated = await rejectBarangayApplication(application.id, reason);
            clearProofDownload(application.id);
            setApplications((current) => current.map((item) => item.id === updated.id ? updated : item).filter((item) => filter !== 'PENDING' || item.status === 'PENDING'));
            setCount((current) => filter === 'PENDING' ? Math.max(0, current - 1) : current);
            setMessage({ type: 'success', text: `Application KB-${updated.id} rejected and the reason was recorded.` });
        } catch (error) {
            setMessage({ type: 'error', text: apiErrorMessage(error, 'Could not reject this application.') });
        } finally {
            setBusyId(null);
        }
    };

    const totalPages = Math.max(1, Math.ceil(count / 50));

    return (
        <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-8">
            <header className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    {(user?.is_superuser || user?.role === 'BARANGAY_OPERATOR') && <Link to={user?.is_superuser ? "/platform/accounts" : "/operator/accounts"} className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-primary-text hover:underline">
                        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Account support
                    </Link>}
                    <p className="mt-3 text-xs font-bold uppercase tracking-[0.16em] text-primary-text">Barangay identity review</p>
                    <h1 className="mt-1 flex items-center gap-3 text-2xl font-extrabold text-slate-900 sm:text-3xl">
                        <Building2 className="h-7 w-7 text-primary-text" aria-hidden="true" /> Barangay onboarding review
                    </h1>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                        Review requests for Barangays without an Admin account. Verify the official and locality through an independent official channel before approving. Approval creates or matches the Barangay tenant and activates the applicant’s existing account.
                    </p>
                </div>
                <button type="button" onClick={() => void logout()} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                    <LogOut className="h-4 w-4" aria-hidden="true" /> Log out
                </button>
            </header>

            <aside className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
                <p>Applicant contact details are visible only to Barangay Operators and controlled platform superusers. Do not approve from this form alone: independently verify the official and Barangay. This review grants no access to resident or service records. Existing Barangay Admins manage Field Officials from staff management.</p>
            </aside>

            {message && <p role={message.type === 'error' ? 'alert' : 'status'} className={`rounded-lg border p-3 text-sm ${message.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-900'}`}>{message.text}</p>}

            <section className="flex flex-wrap items-end justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div>
                    <label htmlFor="application-status" className="block text-sm font-semibold text-slate-700">Application status</label>
                    <select id="application-status" value={filter} onChange={(event) => { setFilter(event.target.value as BarangayApplicationStatus); setPage(1); setMessage(null); }} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:w-64 md:text-sm">
                        <option value="PENDING">Pending review</option>
                        <option value="APPROVED">Approved</option>
                        <option value="REJECTED">Rejected</option>
                    </select>
                </div>
                <p className="text-sm text-slate-600">{count} {filter.toLowerCase()} application{count === 1 ? '' : 's'}</p>
            </section>

            {loading ? <p role="status" className="py-8 text-center text-sm text-slate-600">Loading applications…</p> : loadError ? (
                <InlineErrorState message="We couldn't load Barangay applications." onRetry={() => { void loadApplications(true); }} retrying={retrying} />
            ) : applications.length === 0 ? (
                <div role="status" className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">No {filter.toLowerCase()} applications.</div>
            ) : (
                <section aria-label="Barangay onboarding applications" className="space-y-4">
                    {applications.map((application) => (
                        <article key={application.id} className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 bg-slate-50 p-4 sm:p-5">
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Request KB-{application.id} · submitted {dateLabel(application.created_at)}</p>
                                    <h2 className="mt-1 text-lg font-bold text-slate-900">{application.name}</h2>
                                    <p className="text-sm text-slate-600">{application.municipality}, {application.province}</p>
                                </div>
                                <span className={`rounded-full px-3 py-1 text-xs font-bold ${application.status === 'PENDING' ? 'bg-amber-100 text-amber-900' : application.status === 'APPROVED' ? 'bg-emerald-100 text-emerald-900' : 'bg-rose-100 text-rose-900'}`}>
                                    {application.status}
                                </span>
                            </div>

                            <div className="grid gap-4 p-4 sm:grid-cols-2 sm:p-5">
                                <div>
                                    <h3 className="text-xs font-bold uppercase tracking-wide text-slate-500">Proposed first Admin</h3>
                                    <p className="mt-1 font-semibold text-slate-900">{application.applicant_name}</p>
                                    <p className="text-sm text-slate-600">{application.applicant_position}</p>
                                    <p className="mt-2 break-all text-sm text-slate-700">Official sign-in email: <strong>{application.applicant_email}</strong></p>
                                    {application.has_applicant_account && <p className={`mt-1 text-sm font-semibold ${application.email_verified_at ? 'text-emerald-700' : 'text-amber-800'}`}>
                                        {application.email_verified_at ? `Email verified ${dateLabel(application.email_verified_at)}` : 'Email ownership is not verified'}
                                    </p>}
                                    <p className="text-sm text-slate-700">{application.applicant_phone}</p>
                                    {application.admin_username && <p className="mt-2 text-sm text-slate-600">Historical username: <strong className="text-slate-800">@{application.admin_username}</strong></p>}
                                    {application.status === 'PENDING' && application.has_applicant_account && <p className="mt-2 text-sm font-semibold text-amber-800">Applicant account is inactive until approval.</p>}
                                </div>
                                <div className="space-y-2 rounded-lg border border-slate-200 p-3 text-sm text-slate-700">
                                    <p className="flex items-start gap-2"><CheckCircle2 className={`mt-0.5 h-4 w-4 shrink-0 ${application.applicant_authorized ? 'text-emerald-600' : 'text-rose-600'}`} aria-hidden="true" /> Applicant attested that they are authorized to apply.</p>
                                    <p className="flex items-start gap-2"><CheckCircle2 className={`mt-0.5 h-4 w-4 shrink-0 ${application.contact_consent ? 'text-emerald-600' : 'text-rose-600'}`} aria-hidden="true" /> Applicant consented to use of contact details for review.</p>
                                    {application.has_applicant_account && <div className="border-t border-slate-100 pt-2">
                                        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Authority evidence</p>
                                        {application.has_proof_of_authority ? <>
                                            <p className="mt-1 text-sm">Private supporting document is available for pending review.</p>
                                            {application.status === 'PENDING' && <div className="mt-2 flex flex-wrap items-center gap-3">
                                                <button type="button" disabled={proofLoadingId === application.id} onClick={() => void prepareProofDownload(application)} className="inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60">
                                                    {proofLoadingId === application.id ? 'Preparing secure download…' : 'Prepare secure proof download'}
                                                </button>
                                                {proofDownloads[application.id] && <a href={proofDownloads[application.id].url} download={proofDownloads[application.id].filename} className="inline-flex min-h-10 items-center text-sm font-semibold text-primary-text underline">Download proof document</a>}
                                            </div>}
                                        </> : <p className="mt-1 text-sm font-semibold text-rose-700">No proof document is attached.</p>}
                                    </div>}
                                    {application.reviewed_at && <p className="border-t border-slate-100 pt-2 text-xs text-slate-500">Reviewed by {application.reviewed_by_username || 'platform operator'} · {dateLabel(application.reviewed_at)}</p>}
                                    {application.created_barangay_id && <p className="text-xs text-slate-600">Barangay ID: {application.created_barangay_id}</p>}
                                    {application.created_admin_email && <p className="text-xs text-slate-600">Admin sign-in email: {application.created_admin_email}</p>}
                                    {application.created_admin_username && <p className="text-xs text-slate-600">Historical Admin username: @{application.created_admin_username}</p>}
                                    {application.review_note && <p className="border-t border-slate-100 pt-2 text-sm"><strong>Review note:</strong> {application.review_note}</p>}
                                </div>
                            </div>

                            {application.status === 'PENDING' && (
                                <div className="grid gap-4 border-t border-slate-100 bg-white p-4 sm:p-5 lg:grid-cols-2">
                                    <div className="space-y-3">
                                        {application.has_applicant_account && <>
                                            <label className="flex items-start gap-3 text-sm leading-5 text-slate-700">
                                                <input type="checkbox" checked={Boolean(proofReviewed[application.id])} onChange={(event) => setProofReviewed((current) => ({ ...current, [application.id]: event.target.checked }))} disabled={!application.has_proof_of_authority || !application.email_verified_at} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50" />
                                                <span>I inspected the uploaded document and confirmed it supports the applicant’s stated Barangay role.</span>
                                            </label>
                                            {!application.email_verified_at && <p className="rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-900">Approval is unavailable until the applicant verifies their official email.</p>}
                                        </>}
                                        <label className="flex items-start gap-3 text-sm leading-5 text-slate-700">
                                            <input type="checkbox" checked={Boolean(verified[application.id])} onChange={(event) => setVerified((current) => ({ ...current, [application.id]: event.target.checked }))} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus-visible:ring-2 focus-visible:ring-primary" />
                                            <span>I verified the Barangay locality and applicant’s identity through an independent official channel.</span>
                                        </label>
                                        <label htmlFor={`approve-note-${application.id}`} className="block text-sm font-semibold text-slate-700">Approval note <span className="font-normal text-slate-500">(optional)</span></label>
                                        <textarea id={`approve-note-${application.id}`} rows={2} maxLength={1000} value={approvalNotes[application.id] ?? ''} onChange={(event) => setApprovalNotes((current) => ({ ...current, [application.id]: event.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary" />
                                        <button type="button" disabled={!verified[application.id] || (application.has_applicant_account && (!application.has_proof_of_authority || !application.email_verified_at || !proofReviewed[application.id])) || busyId === application.id} onClick={() => void applyReview(application)} className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                                            <ClipboardCheck className="h-4 w-4" aria-hidden="true" /> {busyId === application.id ? 'Approving…' : 'Approve and activate Admin'}
                                        </button>
                                    </div>
                                    <div className="space-y-3">
                                        <label htmlFor={`reject-reason-${application.id}`} className="block text-sm font-semibold text-slate-700">Rejection reason</label>
                                        <textarea id={`reject-reason-${application.id}`} rows={3} minLength={5} maxLength={1000} value={rejectionReasons[application.id] ?? ''} onChange={(event) => setRejectionReasons((current) => ({ ...current, [application.id]: event.target.value }))} placeholder="Record why the request cannot be approved." className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary" />
                                        <button type="button" disabled={(rejectionReasons[application.id]?.trim().length ?? 0) < 5 || busyId === application.id} onClick={() => void reject(application)} className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-rose-300 bg-white px-4 py-2 text-sm font-bold text-rose-800 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2">
                                            <XCircle className="h-4 w-4" aria-hidden="true" /> {busyId === application.id ? 'Saving…' : 'Reject and record reason'}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </article>
                    ))}
                </section>
            )}

            {totalPages > 1 && <nav aria-label="Application pages" className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3">
                <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((current) => current - 1)} className="min-h-11 rounded-lg border border-slate-300 px-4 text-sm font-semibold disabled:opacity-50">Previous</button>
                <span className="text-sm text-slate-600">Page {page} of {totalPages}</span>
                <button type="button" disabled={page >= totalPages || loading} onClick={() => setPage((current) => current + 1)} className="min-h-11 rounded-lg border border-slate-300 px-4 text-sm font-semibold disabled:opacity-50">Next</button>
            </nav>}
        </main>
    );
}
