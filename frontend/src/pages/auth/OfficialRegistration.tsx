import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { axiosPublic } from '../../api/axios';
import { RegisterHeroBanner } from '../../components/auth/register';

interface PublicBarangay {
    id: number;
    name: string;
    municipality: string;
    province: string;
}

export const OfficialRegistration: React.FC = () => {
    const navigate = useNavigate();
    const [barangays, setBarangays] = useState<PublicBarangay[]>([]);
    const [barangaysError, setBarangaysError] = useState('');
    const [loadingBarangays, setLoadingBarangays] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [submitted, setSubmitted] = useState(false);
    const [form, setForm] = useState({ barangay_id: '', applicant_name: '', applicant_position: '', applicant_email: '', applicant_phone: '' });

    const loadBarangays = async () => {
        setLoadingBarangays(true);
        setBarangaysError('');
        try {
            const response = await axiosPublic.get('/auth/public/barangays/');
            const results = Array.isArray(response.data) ? response.data : response.data?.results;
            if (!Array.isArray(results)) throw new Error('Invalid barangay list');
            setBarangays(results);
        } catch {
            setBarangaysError('Approved barangays could not be loaded. Please try again.');
        } finally {
            setLoadingBarangays(false);
        }
    };

    useEffect(() => { void loadBarangays(); }, []);

    const update = (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
    };

    const submit = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setError('');
        setSubmitting(true);
        try {
            await axiosPublic.post('/auth/barangay-applications/', {
                application_type: 'OFFICIAL',
                barangay_id: Number(form.barangay_id),
                applicant_name: form.applicant_name.trim(),
                applicant_position: form.applicant_position.trim(),
                applicant_email: form.applicant_email.trim().toLowerCase(),
                applicant_phone: form.applicant_phone.trim(),
            });
            setSubmitted(true);
        } catch (requestError: any) {
            setError(requestError.response?.data?.detail
                || requestError.response?.data?.applicant_email?.[0]
                || requestError.response?.data?.barangay_id?.[0]
                || requestError.response?.data?.non_field_errors?.[0]
                || 'Could not submit your official account request. Please check your details and try again.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col md:flex-row bg-[#F6F8FC] font-sans">
            <RegisterHeroBanner isAdminMode onToggleMode={() => navigate('/register')} />

            <main className="w-full md:w-7/12 lg:w-[60%] flex flex-col justify-center items-center px-6 py-8 sm:p-12 lg:p-16">
                <div className="w-full max-w-xl">
                    <header className="mb-7">
                        <span className="inline-flex px-3 py-1 rounded-full bg-amber-100 text-amber-900 text-xs font-extrabold uppercase tracking-wider">
                            Authorized Staff
                        </span>
                        <h2 className="mt-3 text-3xl font-extrabold text-slate-900 tracking-tight">Official Registration</h2>
                        <p className="text-slate-500 mt-2">Request an official account for an already onboarded barangay.</p>
                    </header>

                    {submitted ? (
                        <section role="status" className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 space-y-3">
                            <h3 className="text-lg font-bold text-emerald-900">Request submitted for review</h3>
                            <p className="text-sm leading-relaxed text-emerald-900">DILG will verify your official role and barangay. If approved, you will receive an email with instructions to set up your account password.</p>
                        </section>
                    ) : (
                        <form onSubmit={submit} className="space-y-4 rounded-2xl border border-amber-200 bg-white p-5 sm:p-7 shadow-sm">
                            <div className="flex items-center gap-2 text-amber-900">
                                <Shield className="w-5 h-5 text-amber-600" aria-hidden="true" />
                                <h3 className="font-bold">Official account request</h3>
                            </div>
                            {error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
                            {barangaysError && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{barangaysError} <button type="button" onClick={() => void loadBarangays()} className="ml-1 font-bold underline">Retry</button></div>}
                            <label className="block text-sm font-semibold text-slate-700">Barangay
                                <select name="barangay_id" required value={form.barangay_id} onChange={update} disabled={loadingBarangays || barangays.length === 0} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3">
                                    <option value="">{loadingBarangays ? 'Loading approved barangays…' : 'Select your barangay'}</option>
                                    {barangays.map((barangay) => <option key={barangay.id} value={barangay.id}>{barangay.name} — {barangay.municipality}, {barangay.province}</option>)}
                                </select>
                            </label>
                            <label className="block text-sm font-semibold text-slate-700">Full name
                                <input name="applicant_name" required maxLength={255} value={form.applicant_name} onChange={update} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" />
                            </label>
                            <label className="block text-sm font-semibold text-slate-700">Official position
                                <input name="applicant_position" required maxLength={120} value={form.applicant_position} onChange={update} placeholder="e.g. Barangay Secretary" className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" />
                            </label>
                            <label className="block text-sm font-semibold text-slate-700">Email address
                                <input name="applicant_email" required type="email" maxLength={254} value={form.applicant_email} onChange={update} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" />
                            </label>
                            <label className="block text-sm font-semibold text-slate-700">Contact number
                                <input name="applicant_phone" required type="tel" maxLength={30} value={form.applicant_phone} onChange={update} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" />
                            </label>
                            <p className="text-xs leading-relaxed text-slate-600">Account requests are reviewed before an account is created.</p>
                            <button type="submit" disabled={submitting || loadingBarangays || barangays.length === 0} className="min-h-12 w-full rounded-xl bg-[#091B35] px-5 py-3 font-bold text-white hover:bg-[#0F2D59] disabled:opacity-50">{submitting ? 'Submitting…' : 'Submit Official Account Request'}</button>
                        </form>
                    )}

                    <div className="mt-7 space-y-3 text-center text-sm">
                        <p className="text-slate-500">Registering as a resident? <Link to="/register" className="font-bold text-sky-700 underline">Switch to Resident Sign Up</Link></p>
                        <p className="text-slate-500">Already have an account? <Link to="/login" className="font-bold text-slate-900 hover:underline">Log in here</Link></p>
                    </div>
                </div>
            </main>
        </div>
    );
};
