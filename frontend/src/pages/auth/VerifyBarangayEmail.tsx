import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, MailCheck, ShieldCheck } from 'lucide-react';
import {
    resendBarangayApplicationVerification,
    verifyBarangayApplicationEmail,
} from '../../api/barangayOnboarding';

function apiMessage(error: unknown, fallback: string) {
    if (!error || typeof error !== 'object' || !('response' in error)) return fallback;
    const response = error as { response?: { data?: { detail?: unknown } } };
    return typeof response.response?.data?.detail === 'string'
        ? response.response.data.detail
        : fallback;
}

export function VerifyBarangayEmail() {
    const [searchParams] = useSearchParams();
    const applicationId = Number(searchParams.get('application'));
    const token = new URLSearchParams(window.location.hash.slice(1)).get('token') ?? '';
    const [email, setEmail] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [resending, setResending] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState(token ? '' : 'This verification link is incomplete. Request a new link from your application confirmation page.');
    const [verified, setVerified] = useState(false);

    const confirm = async () => {
        if (!Number.isInteger(applicationId) || applicationId < 1 || !token) {
            setError('This verification link is incomplete. Request a new link from your application confirmation page.');
            return;
        }
        setSubmitting(true);
        setError('');
        try {
            const result = await verifyBarangayApplicationEmail(applicationId, token);
            setVerified(true);
            setMessage(result.detail);
            window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
        } catch (requestError) {
            setError(apiMessage(requestError, 'This link may be expired or already used. Request a new verification link below.'));
        } finally {
            setSubmitting(false);
        }
    };

    const resend = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!Number.isInteger(applicationId) || applicationId < 1) {
            setError('The application reference is missing. Return to the application form or contact KapitBayan support.');
            return;
        }
        setResending(true);
        setError('');
        try {
            const result = await resendBarangayApplicationVerification(applicationId, email.trim().toLowerCase());
            setMessage(result.detail);
        } catch (requestError) {
            setError(apiMessage(requestError, 'We could not request a new link. Wait and try again.'));
        } finally {
            setResending(false);
        }
    };

    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
            <section className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
                <Link to="/official-login" className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-primary-text hover:underline">
                    <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Official sign in
                </Link>
                <div className="mt-5 flex items-center gap-3 text-primary-text">
                    {verified ? <CheckCircle2 className="h-7 w-7" aria-hidden="true" /> : <ShieldCheck className="h-7 w-7" aria-hidden="true" />}
                    <h1 className="text-2xl font-extrabold text-slate-900">Verify official email</h1>
                </div>

                {verified ? (
                    <p role="status" className="mt-4 rounded-lg bg-emerald-50 p-4 text-sm leading-6 text-emerald-900">{message} You will be able to sign in after DILG approves the application.</p>
                ) : (
                    <>
                        <p className="mt-4 text-sm leading-6 text-slate-600">Confirm that you can receive mail at the official email on the Barangay Admin application. Opening this page does not verify it; select the button below to confirm.</p>
                        {error && <p role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
                        <button type="button" onClick={() => void confirm()} disabled={submitting} className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60">
                            <MailCheck className="h-4 w-4" aria-hidden="true" /> {submitting ? 'Verifying…' : 'Verify email'}
                        </button>
                    </>
                )}

                {!verified && (
                    <form onSubmit={(event) => void resend(event)} className="mt-6 border-t border-slate-100 pt-5">
                        <h2 className="text-sm font-bold text-slate-900">Need another link?</h2>
                        <p className="mt-1 text-xs leading-5 text-slate-500">Enter the official email used for this application. The same response is shown whether or not a link can be sent. Links can be requested once every 10 minutes.</p>
                        <label htmlFor="verification-email" className="mt-3 block text-sm font-semibold text-slate-700">Official email</label>
                        <input id="verification-email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:text-sm" />
                        <button type="submit" disabled={resending} className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60">
                            {resending ? 'Requesting…' : 'Request new verification link'}
                        </button>
                    </form>
                )}
                {message && !verified && <p role="status" className="mt-4 rounded-lg bg-blue-50 p-3 text-sm leading-5 text-blue-900">{message}</p>}
            </section>
        </main>
    );
}
