import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, CheckCircle, Shield } from 'lucide-react';
import { axiosPublic } from '../../api/axios';
import { getSafeApiErrorMessage } from '../../api/error-message';

export const SetPassword = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const uidb64 = searchParams.get('uidb64');
    const token = searchParams.get('token');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (password !== confirmPassword) {
            setErrorMessage('Passwords do not match.');
            setStatus('error');
            return;
        }

        if (password.length < 8) {
            setErrorMessage('Password must be at least 8 characters.');
            setStatus('error');
            return;
        }

        setStatus('loading');
        setErrorMessage('');
        try {
            await axiosPublic.post('/auth/password-reset/confirm/', {
                new_password: password,
                uidb64,
                token,
            });
            setStatus('success');
            window.setTimeout(() => navigate('/login'), 3000);
        } catch (error: unknown) {
            setStatus('error');
            const response = (error as { response?: { status?: number; data?: { token?: string[] } } })?.response;
            const tokenError = response?.status && response.status < 500 ? response.data?.token?.[0] : undefined;
            setErrorMessage(tokenError || getSafeApiErrorMessage(
                error,
                'We could not set your password. The link may have expired; ask your Barangay Admin to resend the invitation.',
            ));
        }
    };

    if (!uidb64 || !token) {
        return (
            <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
                <section className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-sm">
                    <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-amber-600" aria-hidden="true" />
                    <h1 className="mb-2 text-xl font-bold text-slate-900">Invalid Setup Link</h1>
                    <p className="text-sm text-slate-600">This account setup link is incomplete. Ask your Barangay Admin to resend the invitation.</p>
                    <Link to="/login" className="mt-6 inline-block text-sm font-semibold text-blue-700 hover:underline">Back to Login</Link>
                </section>
            </main>
        );
    }

    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
            <section className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm">
                <div className="mb-6 flex justify-center">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
                        <Shield className="h-6 w-6 text-blue-700" aria-hidden="true" />
                    </div>
                </div>
                <h1 className="mb-2 text-center text-2xl font-bold text-slate-900">Set Your Password</h1>
                <p className="mb-8 text-center text-sm text-slate-600">Create a password to finish setting up your KapitBayan account.</p>

                {status === 'success' ? (
                    <div className="flex items-center gap-3 rounded-xl bg-emerald-50 p-4 text-emerald-800" role="status">
                        <CheckCircle className="h-5 w-5 shrink-0" aria-hidden="true" />
                        <p className="text-sm font-semibold">Your password is set. You can now sign in. Redirecting to login…</p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        {status === 'error' && (
                            <div role="alert" className="rounded-lg border border-red-100 bg-red-50 p-3 text-sm text-red-700">
                                {errorMessage}
                            </div>
                        )}
                        <label className="block text-sm font-semibold text-slate-700">
                            New Password
                            <input
                                type="password"
                                required
                                minLength={8}
                                autoComplete="new-password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-blue-600"
                            />
                        </label>
                        <label className="block text-sm font-semibold text-slate-700">
                            Confirm Password
                            <input
                                type="password"
                                required
                                minLength={8}
                                autoComplete="new-password"
                                value={confirmPassword}
                                onChange={(event) => setConfirmPassword(event.target.value)}
                                className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-blue-600"
                            />
                        </label>
                        <button
                            type="submit"
                            disabled={status === 'loading'}
                            className="w-full rounded-xl bg-blue-700 px-4 py-3 font-bold text-white transition-colors hover:bg-blue-800 disabled:opacity-50"
                        >
                            {status === 'loading' ? 'Setting Password…' : 'Set Password'}
                        </button>
                    </form>
                )}
            </section>
        </main>
    );
};
