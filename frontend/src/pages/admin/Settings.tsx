import toast from 'react-hot-toast';
import React, { useCallback, useEffect, useState } from 'react';
import { Bell, Shield, Key, Smartphone, Laptop, Trash2, Clock, MapPin, UserRound } from 'lucide-react';
import { ChangePasswordModal } from '../../components/modals/ChangePasswordModal';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { axiosPrivate } from '../../api/axios';

interface RefreshSession {
    id: number
    ip_address: string
    user_agent: string
    created_at: string
    expires_at: string
    is_revoked: boolean
}

interface LoginEvent {
    id: number;
    username: string;
    role: string;
    ip_address: string | null;
    user_agent: string;
    created_at: string;
}

export const Settings: React.FC = () => {
    const [emailAlerts, setEmailAlerts] = useState(true);
    const [pushAlerts, setPushAlerts] = useState(false);
    const [isLoadingProfile, setIsLoadingProfile] = useState(true)
    const [profileLoadError, setProfileLoadError] = useState(false)
    const [isRetryingProfile, setIsRetryingProfile] = useState(false)
    const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false)

    const [sessions, setSessions] = useState<RefreshSession[]>([])
    const [isLoadingSessions, setIsLoadingSessions] = useState(true)
    const [sessionsLoadError, setSessionsLoadError] = useState(false)
    const [isRetryingSessions, setIsRetryingSessions] = useState(false)

    const [loginEvents, setLoginEvents] = useState<LoginEvent[]>([])
    const [isLoadingLoginEvents, setIsLoadingLoginEvents] = useState(true)
    const [loginEventsLoadError, setLoginEventsLoadError] = useState(false)
    const [isRetryingLoginEvents, setIsRetryingLoginEvents] = useState(false)

    const fetchProfile = useCallback(async (isRetry = false) => {
        if (isRetry) setIsRetryingProfile(true)

        try {
            const response = await axiosPrivate.get('/auth/me/')
            setEmailAlerts(response.data.email_alerts)
            setPushAlerts(response.data.push_alerts)
            setProfileLoadError(false)
        } catch (error) {
            console.error("Failed to load profile preferences", error)
            setProfileLoadError(true)
        } finally {
            setIsLoadingProfile(false)
            setIsRetryingProfile(false)
        }
    }, [])

    const fetchSessions = useCallback(async (isRetry = false) => {
        if (isRetry) setIsRetryingSessions(true)

        try {
            const response = await axiosPrivate.get('/auth/sessions/')
            // Handle DRF global pagination by extracting the 'results' array if present
            const sessionData = response.data.results ? response.data.results : response.data
            setSessions(sessionData)
            setSessionsLoadError(false)
        } catch (error) {
            console.error("Failed to fetch sessions", error)
            setSessionsLoadError(true)
        } finally {
            setIsLoadingSessions(false)
            setIsRetryingSessions(false)
        }
    }, [])

    const fetchLoginEvents = useCallback(async (isRetry = false) => {
        if (isRetry) setIsRetryingLoginEvents(true)

        try {
            const response = await axiosPrivate.get('/auth/login-events/')
            const eventData = response.data.results ?? response.data
            if (!Array.isArray(eventData)) throw new Error('Invalid sign-in history response.')
            setLoginEvents(eventData)
            setLoginEventsLoadError(false)
        } catch (error) {
            console.error("Failed to fetch sign-in history", error)
            setLoginEventsLoadError(true)
        } finally {
            setIsLoadingLoginEvents(false)
            setIsRetryingLoginEvents(false)
        }
    }, [])

    useEffect(() => {
        void fetchProfile()
    }, [fetchProfile])

    useEffect(() => {
        void fetchSessions()
    }, [fetchSessions])

    useEffect(() => {
        void fetchLoginEvents()
    }, [fetchLoginEvents])

    const handleToggleEmail = async () => {
        const newValue = !emailAlerts
        try {
            await axiosPrivate.patch('/auth/me/', { email_alerts: newValue })
            setEmailAlerts(newValue) // Only update UI if the backend request succeeds
        } catch {
            toast.error('Failed to update email preferences.')
        }
    }

    const handleTogglePush = async () => {
        const newValue = !pushAlerts
        try {
            await axiosPrivate.patch('/auth/me/', { push_alerts: newValue })
            setPushAlerts(newValue)
        } catch {
            toast.error('Failed to update push preferences.')
        }
    }
    const handleRevokeSession = async (id: number) => {
        try {
            await axiosPrivate.delete(`/auth/session/${id}/`)
            setSessions(sessions.filter(session => session.id !== id))
        } catch {
            toast.error('Failed to revoke session. It may have already expired.')
        }
    }
    return (
        <div className="max-w-4xl mx-auto space-y-6 pb-12">
            <div>
                <h1 className="text-2xl font-extrabold text-[#0f172a] tracking-tight">System Settings</h1>
                <p className="text-[#64748b] text-sm mt-1">Manage your dashboard preferences and security.</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden divide-y divide-slate-100">
                {/* Notifications Section */}
                <div className="p-8">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center text-orange-600">
                            <Bell className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-900">Notifications</h2>
                            <p className="text-xs text-slate-500">Control when and how you are alerted.</p>
                        </div>
                    </div>

                    {isLoadingProfile ? (
                        <div className="text-sm text-slate-500 animate-pulse">Loading notification preferences...</div>
                    ) : profileLoadError ? (
                        <InlineErrorState
                            message="Could not load notification preferences."
                            onRetry={() => { void fetchProfile(true); }}
                            retrying={isRetryingProfile}
                        />
                    ) : (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Smartphone className="w-4 h-4 text-slate-400" />
                                    <span className="text-sm font-semibold text-slate-700">Push Notifications (Queue Alerts)</span>
                                </div>
                                <button
                                    onClick={handleTogglePush}
                                    disabled={isLoadingProfile}
                                    className={`w-11 h-6 rounded-full transition-colors relative disabled:opacity-50 ${pushAlerts ? 'bg-orange-500' : 'bg-slate-200'}`}
                                >
                                    <div className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full transition-transform ${pushAlerts ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                </button>
                            </div>

                            <div className="flex items-center justify-between">
                                <div className="flex flex-col">
                                    <span className="text-sm font-semibold text-slate-700">Email Summaries</span>
                                    <span className="text-[10px] text-slate-400">Receive daily queue and request reports</span>
                                </div>
                                <button
                                    onClick={handleToggleEmail}
                                    disabled={isLoadingProfile}
                                    className={`w-11 h-6 rounded-full transition-colors relative disabled:opacity-50 ${emailAlerts ? 'bg-orange-500' : 'bg-slate-200'}`}
                                >
                                    <div className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full transition-transform ${emailAlerts ? 'translate-x-5' : 'translate-x-0'}`}></div>
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Security Section */}
                <div className="p-8">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
                            <Shield className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-900">Security</h2>
                            <p className="text-xs text-slate-500">Protect your administrative account.</p>
                        </div>
                    </div>

                    <div className="flex items-center justify-between py-3">
                        <div className="flex items-center gap-3">
                            <Key className="w-4 h-4 text-slate-400" />
                            <span className="text-sm font-semibold text-slate-700">Change Password</span>
                        </div>
                        <button
                            onClick={() => setIsPasswordModalOpen(true)}
                            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg transition-colors"
                        >
                            Update
                        </button>
                    </div>

                    <div className="pt-6 mt-6 border-t border-slate-100">
                        <h3 className="text-sm font-bold text-slate-900 mb-4">Active Sessions</h3>
                        {isLoadingSessions ? (
                            <div className="text-sm text-slate-500 animate-pulse">Loading sessions...</div>
                        ) : sessionsLoadError ? (
                            <InlineErrorState
                                message="Could not load active sessions."
                                onRetry={() => { void fetchSessions(true); }}
                                retrying={isRetryingSessions}
                            />
                        ) : sessions.length === 0 ? (
                            <div className="text-sm text-slate-500">No active sessions found.</div>
                        ) : (
                            <div className="space-y-3">
                                {sessions.map((session) => (
                                    <div key={session.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 bg-white rounded-lg shadow-sm">
                                                {session.user_agent.toLowerCase().includes('mobile') ? (
                                                    <Smartphone className="w-4 h-4 text-slate-500" />
                                                ) : (
                                                    <Laptop className="w-4 h-4 text-slate-500" />
                                                )}
                                            </div>
                                            <div>
                                                <div className="text-sm font-semibold text-slate-700">
                                                    {session.user_agent.split(' ')[0] || 'Unknown Device'}
                                                </div>
                                                <div className="flex items-center gap-2 mt-0.5">
                                                    <span className="text-[10px] text-slate-500 bg-slate-200 px-1.5 py-0.5 rounded">
                                                        {session.ip_address}
                                                    </span>
                                                    <span className="flex items-center text-[10px] text-slate-400">
                                                        <Clock className="w-3 h-3 mr-1 inline" />
                                                        {new Date(session.created_at).toLocaleDateString()}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>

                                        <button
                                            onClick={() => handleRevokeSession(session.id)}
                                            className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors group"
                                            title="Revoke Session"
                                        >
                                            <Trash2 className="w-4 h-4 group-hover:scale-110 transition-transform" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="pt-6 mt-6 border-t border-slate-100">
                        <h3 className="text-sm font-bold text-slate-900 mb-1">Recent sign-ins</h3>
                        <p className="mb-4 text-xs leading-5 text-slate-500">
                            Shows successful sign-ins for your account and, for Barangay Admins, Field Officials assigned to your Barangay. IP addresses are approximate network information, not GPS location.
                        </p>
                        {isLoadingLoginEvents ? (
                            <div role="status" className="text-sm text-slate-500 animate-pulse">Loading sign-in history...</div>
                        ) : loginEventsLoadError ? (
                            <InlineErrorState
                                message="Could not load sign-in history."
                                onRetry={() => { void fetchLoginEvents(true); }}
                                retrying={isRetryingLoginEvents}
                            />
                        ) : loginEvents.length === 0 ? (
                            <div className="text-sm text-slate-500">No successful sign-ins recorded yet.</div>
                        ) : (
                            <ul className="space-y-3" aria-label="Recent sign-ins">
                                {loginEvents.map((event) => (
                                    <li key={event.id} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                            <div className="flex min-w-0 items-center gap-2">
                                                <UserRound className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
                                                <span className="truncate text-sm font-semibold text-slate-700">{event.username || 'Unknown account'}</span>
                                                <span className="rounded bg-white px-1.5 py-0.5 text-[10px] font-semibold text-slate-500">{event.role.replaceAll('_', ' ')}</span>
                                            </div>
                                            <span className="flex items-center text-xs text-slate-500">
                                                <Clock className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
                                                {new Date(event.created_at).toLocaleString()}
                                            </span>
                                        </div>
                                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                                            <span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" aria-hidden="true" /> IP: {event.ip_address || 'Unavailable'}</span>
                                            <span className="max-w-full truncate" title={event.user_agent || 'Unknown device'}>{event.user_agent || 'Unknown device'}</span>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                </div>
            </div>
            {/* Render the Modal here */}
            <ChangePasswordModal
                isOpen={isPasswordModalOpen}
                onClose={() => setIsPasswordModalOpen(false)}
                onSuccess={() => {
                    setIsPasswordModalOpen(false);
                    toast.success('Password updated successfully!');
                }}
            />
        </div>
    );
};

