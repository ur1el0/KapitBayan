import React, { useState} from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { axiosPublic } from "../../api/axios";
import { getSafeApiErrorMessage } from "../../api/error-message";
import { Shield, CheckCircle, AlertTriangle } from "lucide-react";
import { LanguageSwitcher } from "../../components/language/LanguageSwitcher";
import { useLanguage } from "../../context/language-context";

export const ResetPassword = () => {
    const { t } = useLanguage();
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()

    // Extract the cryptographic tokens from the URL
    const uidb64 = searchParams.get('uidb64')
    const token = searchParams.get('token')

    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
    const [errorMessage, setErrorMessage] = useState('')

    const handleSubmit = async (e: React.SubmitEvent<HTMLElement>) => {
        e.preventDefault()

        if(password !== confirmPassword) {
            setErrorMessage(t("Passwords do not match."))
            setStatus('error')
            return
        }

        if (password.length < 8) {
            setErrorMessage(t("Password must be at least 8 characters."))
            setStatus('error')
            return
        }

        setStatus('loading')
        try {
            await axiosPublic.post('/auth/password-reset/confirm/', {
                new_password: password,
                uidb64,
                token
            })
            setStatus('success')
            setTimeout(() => navigate('/login'), 3000)
        } catch (error: any) {
            setStatus('error')
            const tokenError = error.response?.status < 500 ? error.response?.data?.token?.[0] : undefined
            setErrorMessage(tokenError ? t(tokenError) : getSafeApiErrorMessage(
                error,
                t("We couldn't reset your password. Try again or request a new reset link."),
            ))
        }
    }

    if (!uidb64 || !token) {
        return (
            <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
                <div className="bg-white p-8 rounded-2xl shadow-sm text-center max-w-md w-full">
                    <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <div className="mb-5 flex justify-end"><LanguageSwitcher compact /></div>
                    <h2 className="text-xl font-bold text-slate-900 mb-2">{t('Invalid Reset Link')}</h2>
                    <p className="text-slate-500 text-sm">{t('This password reset link is malformed or missing security tokens. Please request a new email.')}</p>
                </div>
            </div>
        );
    }
    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
            <div className="bg-white p-8 rounded-2xl shadow-sm max-w-md w-full">
                <div className="mb-5 flex justify-end"><LanguageSwitcher compact /></div>
                <div className="flex justify-center mb-6">
                    <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                        <Shield className="w-6 h-6 text-blue-700" />
                    </div>
                </div>
                                
                <h1 className="text-2xl font-bold text-center text-slate-900 mb-2">{t('Reset Password')}</h1>
                <p className="text-sm text-center text-slate-500 mb-8">{t('Enter a new secure password for your account.')}</p>
                {status === 'success' ? (
                    <div className="bg-emerald-50 text-emerald-700 p-4 rounded-xl flex items-center gap-3">
                        <CheckCircle className="w-5 h-5 shrink-0" />
                        <p className="text-sm font-semibold">{t('Password updated securely! Redirecting to login...')}</p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        {status === 'error' && (
                            <div role="alert" className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                                {errorMessage}
                            </div>
                        )}
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-1.5">{t('New Password')}</label>
                            <input 
                                type="password" 
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none transition-all"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-1.5">{t('Confirm Password')}</label>
                            <input 
                                type="password" 
                                required
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none transition-all"
                            />
                        </div>
                        <button 
                            type="submit" 
                            disabled={status === 'loading'}
                            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold rounded-xl transition-colors"
                        >
                            {status === 'loading' ? t('Securing Account...') : t('Reset Password')}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
}
