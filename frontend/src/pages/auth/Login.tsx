import React, { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/auth-context';
import { axiosPublic } from '../../api/axios';
import { getSafeApiErrorMessage } from '../../api/error-message';
import { Shield, FileCheck2, Clock, Users, KeyRound } from 'lucide-react';

export const Login: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login, logout } = useAuth();
    const location = useLocation();
    const navigate = useNavigate();
    const isAdminMode = location.pathname === '/official-login';

    const handleLogin = async (e: React.SubmitEvent<HTMLElement>) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await axiosPublic.post('/auth/login/', {
                username: username,
                password: password,
            });

            const { access, user: userData } = response.data;

            const isAllowedForWeb = userData?.is_superuser === true
                ? isAdminMode
                : isAdminMode
                    ? userData?.role === 'ADMIN' || userData?.role === 'DILG_ADMIN'
                    : userData?.role === 'RESIDENT';

            if (!isAllowedForWeb) {
                try {
                    // Login sets an HttpOnly refresh cookie before the web client
                    // checks the role. Clear that browser session when the role
                    // belongs in another client.
                    await logout();
                } catch {
                    // The role denial remains in place if cleanup cannot reach the API.
                }

                if (userData?.role === 'FIELD_OFFICIAL') {
                    setError('Field Official accounts must use the KapitBayan mobile app. Web access is not available for this role.');
                } else if (!isAdminMode) {
                    setError('Administrative officials must sign in through the official sign-in page.');
                } else {
                    setError('Resident accounts are not authorized to access the Barangay Authority Command.');
                }
                return;
            }

            if (access) {
                login(access, userData);
                if (userData?.is_superuser === true) {
                    navigate('/platform/accounts');
                } else if (userData?.role === 'DILG_ADMIN') {
                    navigate('/dilg/barangay-applications');
                } else if (userData?.role === 'RESIDENT') {
                    navigate('/portal/documents');
                } else {
                    navigate('/dashboard');
                }
            } else {
                setError('Login failed: Authentication token was not returned.');
            }
        } catch (err) {
            setError(getSafeApiErrorMessage(
                err,
                "We couldn't sign you in. Check your connection and credentials, then try again.",
            ));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col md:flex-row bg-[#F6F8FC] font-sans">
            {/* Left Sidebar Banner */}
            <div
                className={`w-full md:w-5/12 lg:w-[40%] text-white p-5 md:p-8 lg:p-14 flex flex-col justify-between relative overflow-hidden md:min-h-screen transition-all duration-500 ${
                    isAdminMode
                        ? 'bg-gradient-to-b from-[#091B35] via-[#0F2D59] to-[#001128]'
                        : 'bg-gradient-to-b from-[#0284C7] via-[#0369A1] to-[#075985]'
                }`}
            >
                {/* Subtle Decorative Background Wave Pattern */}
                <div className="absolute inset-0 opacity-10 pointer-events-none overflow-hidden">
                    <svg className="w-full h-full" viewBox="0 0 500 800" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M-100 200 C 100 400, 300 100, 600 300 C 900 500, 700 800, 1000 700" stroke="white" strokeWidth="2" fill="none" />
                        <path d="M-50 400 C 150 600, 350 300, 650 500 C 950 700, 750 1000, 1050 900" stroke="white" strokeWidth="2" fill="none" />
                        <path d="M-150 0 C 50 200, 250 -100, 550 100 C 850 300, 650 600, 950 500" stroke="white" strokeWidth="2" fill="none" />
                    </svg>
                </div>

                {/* Brand header */}
                <div className="relative z-10 flex items-center justify-between">
                    <span className="font-bold text-lg tracking-tight text-white sm:text-2xl">
                        KapitBayan
                    </span>
                </div>

                {/* Middle Main Content (Hidden on mobile, visible on tablet/desktop) */}
                <div className="relative z-10 my-auto py-8 hidden md:block">
                    <h1 className="text-4xl lg:text-[2.75rem] font-extrabold text-white tracking-tight leading-[1.15] mb-4">
                        {isAdminMode ? (
                            <>
                                Barangay<br />
                                Authority<br />
                                Command
                            </>
                        ) : (
                            <>
                                Resident<br />
                                Self-Service<br />
                                Portal
                            </>
                        )}
                    </h1>
                    <p className="text-blue-100/80 text-sm lg:text-base font-normal max-w-sm mb-10 leading-relaxed">
                        {isAdminMode
                            ? 'Sign in to Barangay operations or review new Barangay onboarding requests.'
                            : 'Request official clearances, join the live lobby queue, and access community services.'}
                    </p>

                    {/* Feature List */}
                    <div className="space-y-4">
                        {isAdminMode ? (
                            <>
                                <div className="flex items-center gap-3.5">
                                    <div className="w-9 h-9 rounded-lg bg-white/10 backdrop-blur-sm border border-white/10 flex items-center justify-center text-white shrink-0">
                                        <Shield className="w-5 h-5 text-amber-300" />
                                    </div>
                                    <span className="text-[11px] lg:text-xs font-semibold tracking-wider text-blue-100/90 uppercase">
                                        OFFICIAL EMAIL ACCESS
                                    </span>
                                </div>
                                <div className="flex items-center gap-3.5">
                                    <div className="w-9 h-9 rounded-lg bg-white/10 backdrop-blur-sm border border-white/10 flex items-center justify-center text-white shrink-0">
                                        <KeyRound className="w-5 h-5 text-amber-300" />
                                    </div>
                                    <span className="text-[11px] lg:text-xs font-semibold tracking-wider text-blue-100/90 uppercase">
                                        BARANGAY ONBOARDING REVIEW
                                    </span>
                                </div>
                            </>
                        ) : (
                            <>
                                <div className="flex items-center gap-3.5">
                                    <div className="w-9 h-9 rounded-lg bg-white/10 backdrop-blur-sm border border-white/10 flex items-center justify-center text-white shrink-0">
                                        <FileCheck2 className="w-5 h-5 text-sky-200" />
                                    </div>
                                    <span className="text-[11px] lg:text-xs font-semibold tracking-wider text-blue-100/90 uppercase">
                                        OFFICIAL DOCUMENT CLEARANCES
                                    </span>
                                </div>
                                <div className="flex items-center gap-3.5">
                                    <div className="w-9 h-9 rounded-lg bg-white/10 backdrop-blur-sm border border-white/10 flex items-center justify-center text-white shrink-0">
                                        <Clock className="w-5 h-5 text-sky-200" />
                                    </div>
                                    <span className="text-[11px] lg:text-xs font-semibold tracking-wider text-blue-100/90 uppercase">
                                        LIVE LOBBY QUEUE TRACKER
                                    </span>
                                </div>
                                <div className="flex items-center gap-3.5">
                                    <div className="w-9 h-9 rounded-lg bg-white/10 backdrop-blur-sm border border-white/10 flex items-center justify-center text-white shrink-0">
                                        <Users className="w-5 h-5 text-sky-200" />
                                    </div>
                                    <span className="text-[11px] lg:text-xs font-semibold tracking-wider text-blue-100/90 uppercase">
                                        COMMUNITY PROGRAMS & BULLETINS
                                    </span>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Right Login Section */}
            <div className="w-full md:w-7/12 lg:w-[60%] flex flex-col justify-center items-center px-6 py-8 sm:p-12 lg:p-16">
                <div className="w-full max-w-md">
                    {/* Welcome Header */}
                    <div className="mb-8">
                        <div className="flex items-center gap-2 mb-2">
                            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider ${
                                isAdminMode ? 'bg-amber-100 text-amber-900' : 'bg-sky-100 text-sky-900'
                            }`}>
                                {isAdminMode ? 'Official Personnel' : 'Resident Access'}
                            </span>
                        </div>
                        <h2 className="text-3xl lg:text-4xl font-extrabold text-slate-900 tracking-tight">
                            {isAdminMode ? 'Staff Sign In' : 'Welcome Back'}
                        </h2>
                        <p className="text-slate-500 text-sm mt-2 font-normal">
                            {isAdminMode
                                ? 'Enter your administrative credentials to access the operations desk.'
                                : 'Please enter your credentials to access your barangay portal.'}
                        </p>
                    </div>

                    {/* Error Alert */}
                    {error && (
                        <div role="alert" className="mb-6 bg-red-50/90 border border-red-200 rounded-xl p-4 flex items-center gap-3">
                            <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p className="text-sm font-medium text-red-700">{error}</p>
                        </div>
                    )}

                    {/* Login Form */}
                    <form className="space-y-5" onSubmit={handleLogin}>
                        {/* Username Field */}
                        <div>
                            <label className="block text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-2">
                                {isAdminMode ? 'OFFICIAL EMAIL' : 'USERNAME OR EMAIL'}
                            </label>
                            <div className="relative flex items-center">
                                <div className="absolute left-3.5 text-slate-400 pointer-events-none">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.75">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                    </svg>
                                </div>
                                <input
                                    type={isAdminMode ? 'email' : 'text'}
                                    required
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="w-full pl-11 pr-4 py-3.5 bg-[#EEF2F6] focus:bg-white border border-transparent focus:border-[#0284C7] focus:ring-1 focus:ring-[#0284C7] rounded-xl text-sm font-medium text-slate-900 placeholder-slate-400 outline-none transition-all"
                                    placeholder={isAdminMode ? 'Enter your official email' : 'Enter your username or email'}
                                />
                            </div>
                        </div>

                        {/* Password Field */}
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <label className="block text-[11px] font-bold tracking-wider text-slate-500 uppercase">
                                    PASSWORD
                                </label>
                                <Link to="/forgot-password" className="text-xs font-bold text-[#0284C7] hover:underline transition-colors">
                                    Forgot password?
                                </Link>
                            </div>
                            <div className="relative flex items-center">
                                <div className="absolute left-3.5 text-slate-400 pointer-events-none">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="1.75">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                    </svg>
                                </div>
                                <input
                                    type="password"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full pl-11 pr-4 py-3.5 bg-[#EEF2F6] focus:bg-white border border-transparent focus:border-[#0284C7] focus:ring-1 focus:ring-[#0284C7] rounded-xl text-sm font-medium text-slate-900 placeholder-slate-400 outline-none transition-all"
                                    placeholder="........"
                                />
                            </div>
                        </div>

                        {/* Submit Button */}
                        <div className="pt-2">
                            <button
                                type="submit"
                                disabled={loading}
                                className={`w-full py-3.5 px-6 text-white font-bold text-sm rounded-xl shadow-md flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-75 ${
                                    isAdminMode
                                        ? 'bg-[#091B35] hover:bg-[#0F2D59] shadow-[#091B35]/20'
                                        : 'bg-[#0284C7] hover:bg-[#0369A1] shadow-[#0284C7]/25'
                                }`}
                            >
                                <span>
                                    {loading
                                        ? 'Signing in...'
                                        : isAdminMode
                                        ? 'Sign in to Official Portal'
                                        : 'Login to Resident Portal'}
                                </span>
                                {!loading && (
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2.5">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                    </svg>
                                )}
                            </button>
                        </div>
                        
                        {/* Dynamic Register Link */}
                        <div className="text-center pt-3">
                            <p className="text-xs text-slate-500 font-medium">
                                {isAdminMode ? (
                                    <>
                                        Barangay staff accounts are managed by their Barangay Administrator.
                                        <br />
                                        Is your Barangay new to KapitBayan?{' '}
                                        <Link to="/register/barangay" className="font-bold text-slate-900 hover:text-primary hover:underline transition-colors">
                                            Request onboarding
                                        </Link>
                                    </>
                                ) : (
                                    <>
                                        Don't have an account?{' '}
                                        <Link to="/register" className="font-bold text-slate-900 hover:text-[#0284C7] hover:underline transition-colors">
                                            Register as Resident
                                        </Link>
                                    </>
                                )}
                            </p>
                            <p className="mt-3 text-xs text-slate-500">
                                {isAdminMode ? (
                                    <Link to="/login" className="font-semibold text-slate-700 hover:text-primary hover:underline">
                                        Resident sign in
                                    </Link>
                                ) : (
                                    <Link to="/official-login" className="font-semibold text-slate-700 hover:text-primary hover:underline">
                                        Barangay staff sign in
                                    </Link>
                                )}
                            </p>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};
