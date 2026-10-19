import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Building2, CheckCircle2, ClipboardCheck, MailCheck } from 'lucide-react';
import { getSafeApiErrorMessage } from '../../api/error-message';
import {
    submitBarangayApplication,
    resendBarangayApplicationVerification,
    type BarangayApplicationInput,
} from '../../api/barangayOnboarding';

const EMPTY_FORM = {
    name: '',
    municipality: '',
    province: '',
    applicant_name: '',
    applicant_position: '',
    applicant_email: '',
    applicant_phone: '',
    password: '',
    password_confirm: '',
};

function fieldError(error: unknown) {
    if (!error || typeof error !== 'object' || !('response' in error)) return '';
    const response = error as { response?: { status?: number; data?: Record<string, unknown> } };
    const data = response.response?.data;
    if (!data || typeof data !== 'object') return '';
    if (typeof data.detail === 'string') return data.detail;
    for (const key of Object.keys(data)) {
        const value = data[key];
        if (typeof value === 'string') return value;
        if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
    }
    if (response.response?.status === 429) {
        return 'Too many applications were submitted from this connection. Please wait and try again later.';
    }
    return '';
}

export function BarangayOnboarding() {
    const [form, setForm] = useState(EMPTY_FORM);
    const [authorized, setAuthorized] = useState(false);
    const [consent, setConsent] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [applicationId, setApplicationId] = useState<number | null>(null);
    const [proofFile, setProofFile] = useState<File | null>(null);
    const [resending, setResending] = useState(false);
    const [resendMessage, setResendMessage] = useState('');

    const update = (field: keyof typeof EMPTY_FORM, value: string) => {
        setForm((current) => ({ ...current, [field]: value }));
    };

    const submit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setError('');
        setSubmitting(true);
        try {
            if (!proofFile) {
                setError('Upload one proof-of-authority document before submitting.');
                return;
            }
            const payload: BarangayApplicationInput = {
                ...form,
                name: form.name.trim(),
                municipality: form.municipality.trim(),
                province: form.province.trim(),
                applicant_name: form.applicant_name.trim(),
                applicant_position: form.applicant_position.trim(),
                applicant_email: form.applicant_email.trim().toLowerCase(),
                applicant_phone: form.applicant_phone.trim(),
                proof_of_authority: proofFile,
                password: form.password,
                password_confirm: form.password_confirm,
                applicant_authorized: true,
                contact_consent: true,
            };
            if (!authorized || !consent) {
                setError('Confirm your authority and consent before submitting.');
                return;
            }
            const result = await submitBarangayApplication(payload);
            setForm((current) => ({ ...current, password: '', password_confirm: '' }));
            setApplicationId(result.id);
        } catch (requestError) {
            setError(fieldError(requestError) || getSafeApiErrorMessage(
                requestError,
                'We could not submit the application. Check your connection and try again.',
            ));
        } finally {
            setSubmitting(false);
        }
    };

    const resendVerification = async () => {
        if (applicationId === null) return;
        setResending(true);
        setResendMessage('');
        try {
            const result = await resendBarangayApplicationVerification(
                applicationId,
                form.applicant_email.trim().toLowerCase(),
            );
            setResendMessage(result.detail);
        } catch (requestError) {
            setResendMessage(fieldError(requestError) || 'We could not request another link. Please wait and try again.');
        } finally {
            setResending(false);
        }
    };

    const inputClass = 'mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-primary md:text-sm';

    return (
        <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 sm:py-12">
            <div className="mx-auto max-w-3xl">
                <Link to="/official-login" className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-primary-text hover:underline">
                    <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Official sign in
                </Link>

                <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
                    {applicationId === null ? (
                        <>
                            <div className="flex items-start gap-4">
                                <div className="rounded-xl bg-blue-50 p-3 text-primary-text">
                                    <Building2 className="h-6 w-6" aria-hidden="true" />
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-text">New Barangay onboarding</p>
                                    <h1 className="mt-1 text-2xl font-extrabold text-slate-900 sm:text-3xl">Request your Barangay’s first Admin account</h1>
                                    <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                                        Apply using the official’s work email and set the password for that account. A Barangay Operator verifies the Barangay and applicant before the account is activated. Existing Barangays should contact their Admin about Field Official accounts.
                                    </p>
                                </div>
                            </div>

                            {error && <p role="alert" className="mt-6 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}

                            <form onSubmit={(event) => void submit(event)} className="mt-7 space-y-7">
                                <fieldset className="grid gap-4 sm:grid-cols-2">
                                    <legend className="mb-2 text-base font-bold text-slate-900">Barangay locality</legend>
                                    <div className="sm:col-span-2">
                                        <label htmlFor="application-barangay" className="block text-sm font-semibold text-slate-700">Barangay name</label>
                                        <input id="application-barangay" className={inputClass} value={form.name} onChange={(event) => update('name', event.target.value)} autoComplete="organization" maxLength={255} required />
                                    </div>
                                    <div>
                                        <label htmlFor="application-municipality" className="block text-sm font-semibold text-slate-700">Municipality or city</label>
                                        <input id="application-municipality" className={inputClass} value={form.municipality} onChange={(event) => update('municipality', event.target.value)} maxLength={120} required />
                                    </div>
                                    <div>
                                        <label htmlFor="application-province" className="block text-sm font-semibold text-slate-700">Province</label>
                                        <input id="application-province" className={inputClass} value={form.province} onChange={(event) => update('province', event.target.value)} maxLength={120} required />
                                    </div>
                                </fieldset>

                                <fieldset className="grid gap-4 sm:grid-cols-2">
                                    <legend className="mb-2 text-base font-bold text-slate-900">Proposed first Barangay Admin</legend>
                                    <div className="sm:col-span-2">
                                        <label htmlFor="application-official-name" className="block text-sm font-semibold text-slate-700">Official’s full name</label>
                                        <input id="application-official-name" className={inputClass} value={form.applicant_name} onChange={(event) => update('applicant_name', event.target.value)} autoComplete="name" maxLength={255} required />
                                    </div>
                                    <div>
                                        <label htmlFor="application-position" className="block text-sm font-semibold text-slate-700">Official position</label>
                                        <input id="application-position" className={inputClass} value={form.applicant_position} onChange={(event) => update('applicant_position', event.target.value)} maxLength={120} placeholder="For example, Barangay Captain" required />
                                    </div>
                                    <div>
                                        <label htmlFor="application-email" className="block text-sm font-semibold text-slate-700">Official email</label>
                                        <input id="application-email" type="email" className={inputClass} value={form.applicant_email} onChange={(event) => update('applicant_email', event.target.value)} autoComplete="email" maxLength={254} required />
                                    </div>
                                    <div>
                                        <label htmlFor="application-phone" className="block text-sm font-semibold text-slate-700">Official contact number</label>
                                        <input id="application-phone" type="tel" className={inputClass} value={form.applicant_phone} onChange={(event) => update('applicant_phone', event.target.value)} autoComplete="tel" maxLength={30} required />
                                    </div>
                                    <div className="sm:col-span-2">
                                        <label htmlFor="authority-proof" className="block text-sm font-semibold text-slate-700">Proof of official authority</label>
                                        <input id="authority-proof" type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={(event) => setProofFile(event.target.files?.[0] ?? null)} className={`${inputClass} file:mr-3 file:rounded-md file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-primary-text`} required />
                                        <p className="mt-1 text-xs leading-5 text-slate-500">Upload one appointment, designation, authorization, or Barangay endorsement document (PDF, JPEG, or PNG, up to 5 MiB). Do not upload a government ID or resident record. The file is visible only to authorized reviewers and is deleted after a decision.</p>
                                    </div>
                                    <div>
                                        <label htmlFor="application-password" className="block text-sm font-semibold text-slate-700">Set password</label>
                                        <input id="application-password" type="password" className={inputClass} value={form.password} onChange={(event) => update('password', event.target.value)} autoComplete="new-password" minLength={8} required />
                                    </div>
                                    <div>
                                        <label htmlFor="application-password-confirm" className="block text-sm font-semibold text-slate-700">Confirm password</label>
                                        <input id="application-password-confirm" type="password" className={inputClass} value={form.password_confirm} onChange={(event) => update('password_confirm', event.target.value)} autoComplete="new-password" minLength={8} required />
                                    </div>
                                </fieldset>

                                <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                                    <label className="flex items-start gap-3 text-sm leading-5 text-slate-700">
                                        <input type="checkbox" checked={authorized} onChange={(event) => setAuthorized(event.target.checked)} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus-visible:ring-2 focus-visible:ring-primary" required />
                                        <span>I am authorized to request KapitBayan onboarding on behalf of this Barangay.</span>
                                    </label>
                                    <label className="flex items-start gap-3 text-sm leading-5 text-slate-700">
                                        <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus-visible:ring-2 focus-visible:ring-primary" required />
                                        <span>I consent to use the applicant contact details only to review this onboarding request and contact the listed official.</span>
                                    </label>
                                    <p className="text-xs leading-5 text-slate-500">Your official email will be your sign-in identity. We will email a verification link before Barangay Operator review. The password is hashed before storage, and the account stays locked until approval. Do not share your password or enter one-time codes here.</p>
                                </div>

                                <button type="submit" disabled={submitting || !authorized || !consent} className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-bold text-primary-foreground hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 sm:w-auto">
                                    <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
                                    {submitting ? 'Submitting request…' : 'Submit for Barangay Operator review'}
                                </button>
                            </form>
                        </>
                    ) : (
                        <div className="py-6 text-center sm:py-10">
                            <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-600" aria-hidden="true" />
                            <h1 className="mt-4 text-2xl font-extrabold text-slate-900">Application submitted</h1>
                            <p role="status" className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
                                Your request reference is <strong>KB-{applicationId}</strong>. Check the official email inbox and spam folder for a verification link. After verifying your email, a Barangay Operator will review the Barangay and supporting authority document. Your account stays inactive until approval.
                            </p>
                            <button type="button" onClick={() => void resendVerification()} disabled={resending} className="mt-5 inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60">
                                <MailCheck className="h-4 w-4" aria-hidden="true" /> {resending ? 'Requesting…' : 'Resend verification email'}
                            </button>
                            <p role="status" className="mx-auto mt-2 max-w-xl text-xs leading-5 text-slate-500">For privacy, we show the same message either way. A new link can be requested once every 10 minutes.</p>
                            {resendMessage && <p role="status" className="mx-auto mt-2 max-w-xl text-sm text-slate-700">{resendMessage}</p>}
                            <Link to="/official-login" className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary-hover">Return to official sign in</Link>
                        </div>
                    )}
                </section>
            </div>
        </main>
    );
}
