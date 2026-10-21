import React, { useState } from "react";
import { Link } from "react-router-dom";
import { axiosPublic } from "../../api/axios";
import { Mail, ArrowLeft, CheckCircle } from "lucide-react";
import { LanguageSwitcher } from "../../components/language/LanguageSwitcher";
import { useLanguage } from "../../context/language-context";

export const ForgotPassword = () => {
    const { t } = useLanguage();
    const [email, setEmail] = useState('')
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')

    const handleSubmit = async (e: React.SubmitEvent<HTMLElement>) => {
        e.preventDefault()
        setStatus('loading')

        try {
            await axiosPublic.post('/auth/password-reset/', { email })
            setStatus('success')
        } catch {
            // A transport/API failure does not reveal whether this address is registered.
            setStatus('error')
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-slate-50 relative overflow-hidden">
            {/* Background elements */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
                <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-blob"></div>
                <div className="absolute top-48 -left-48 w-96 h-96 bg-indigo-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-blob animation-delay-2000"></div>
            </div>
            <div className="w-full max-w-md bg-white rounded-3xl p-8 sm:p-10 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 z-10">
                <div className="mb-6 flex justify-end"><LanguageSwitcher compact /></div>
                <Link to="/login" className="inline-flex items-center text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors mb-8">
                    <ArrowLeft className="w-4 h-4 mr-1.5" /> {t('Back to Login')}
                </Link>
                <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mb-2">{t('Reset Password')}</h1>
                                
                {status === 'success' ? (
                    <div className="mt-8 text-center">
                        <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                            <CheckCircle className="w-8 h-8 text-emerald-600" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900 mb-2">{t('Check your inbox')}</h3>
                        <p className="text-slate-500 text-sm mb-8">
                            {t('If')} <span className="font-semibold text-slate-700">{email}</span> {t('exists in our system, we have sent a secure password reset link. Check your spam folder too. If it does not arrive, contact your Barangay Administrator to verify the email on your account.')}
                        </p>
                    </div>
                ) : (
                    <>
                        <p className="text-slate-500 text-sm mb-8 font-medium">
                            {t('Enter the email address associated with your account and we will send you a secure link to reset your password.')}
                        </p>
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {status === 'error' && (
                                <p role="alert" className="text-sm font-medium text-red-700">
                                    {t("We couldn't submit your request. Check your connection and try again.")}
                                </p>
                            )}
                            <div className="relative">
                                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                                    <Mail className="w-5 h-5" />
                                </div>
                                <input
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder={t('your.email@example.com')}
                                    className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none transition-all font-medium text-slate-900 placeholder:text-slate-400"
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={status === 'loading'}
                                className="w-full py-4 bg-[#003882] hover:bg-[#002855] text-white font-bold rounded-2xl transition-all shadow-md hover:shadow-lg disabled:opacity-70 disabled:cursor-not-allowed"
                            >
                                {status === 'loading' ? t('Sending Link...') : t('Send Reset Link')}
                            </button>
                        </form>
                    </>
                )}
            </div>
        </div>
    );
}
