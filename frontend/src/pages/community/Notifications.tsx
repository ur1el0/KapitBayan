import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCircle, Clock, AlertTriangle, FileText, Users, UserRoundPlus, Flag, Trash2, CheckSquare, Square, Check, Loader2, ArrowUpRight } from 'lucide-react';
import { axiosPrivate } from '../../api/axios';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import toast from 'react-hot-toast';

interface AdminNotification {
    id: number;
    notification_type: 'queue' | 'document' | 'report' | 'registration' | 'system' | 'alert';
    title: string;
    message: string;
    is_read: boolean;
    created_at: string;
}

const TYPE_CONFIG = {
    queue: { icon: Users, color: 'text-orange-600', bg: 'bg-orange-50' },
    document: { icon: FileText, color: 'text-primary-text', bg: 'bg-primary/10' },
    report: { icon: Flag, color: 'text-rose-600', bg: 'bg-rose-50' },
    registration: { icon: UserRoundPlus, color: 'text-violet-600', bg: 'bg-violet-50' },
    system: { icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    alert: { icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50' },
};

export const Notifications: React.FC = () => {
    const navigate = useNavigate();
    const [notifications, setNotifications] = useState<AdminNotification[]>([]);
    const [selectedIds, setSelectedIds] = useState<number[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [retrying, setRetrying] = useState(false);

    // 1. Fetch notifications from backend
    const fetchNotifications = async (isRetry = false) => {
        if (isRetry) setRetrying(true);

        try {
            const response = await axiosPrivate.get('/admin-notifications/');
            const data = response.data.results || response.data;
            setNotifications(Array.isArray(data) ? data : []);
            setLoadError(false);
        } catch (err) {
            console.error("Failed to fetch notifications:", err);
            setLoadError(true);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    };

    useEffect(() => {
        void fetchNotifications();
    }, []);

    // Selection Logic
    const handleSelectAll = () => {
        if (selectedIds.length === notifications.length && notifications.length > 0) {
            setSelectedIds([]);
        } else {
            setSelectedIds(notifications.map(n => n.id));
        }
    };

    const toggleSelection = (id: number) => {
        setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
    };

    // 2. Action Logic: Mark as Read
    const handleMarkAsRead = async () => {
        try {
            if (selectedIds.length === 0) {
                // Mark all as read via backend custom endpoint
                await axiosPrivate.post('/admin-notifications/mark_all_read/');
                setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
                toast.success("All notifications marked as read.");
            } else {
                // Mark selected as read
                await Promise.all(
                    selectedIds.map(id => axiosPrivate.patch(`/admin-notifications/${id}/`, { is_read: true }))
                );
                setNotifications(prev => prev.map(n => selectedIds.includes(n.id) ? { ...n, is_read: true } : n));
                toast.success(`Marked ${selectedIds.length} notification(s) as read.`);
            }
            setSelectedIds([]);
            window.dispatchEvent(new Event('gridy:admin-notifications-changed'));
        } catch (err) {
            console.error("Failed to update notifications:", err);
            toast.error("Failed to update notification status.");
        }
    };

    const openNotification = async (notification: AdminNotification) => {
        if (!notification.is_read) {
            try {
                await axiosPrivate.patch(`/admin-notifications/${notification.id}/`, { is_read: true });
                setNotifications((current) => current.map((item) =>
                    item.id === notification.id ? { ...item, is_read: true } : item,
                ));
                window.dispatchEvent(new Event('gridy:admin-notifications-changed'));
            } catch {
                toast.error('Could not update the notification.');
                return;
            }
        }

        const routes: Partial<Record<AdminNotification['notification_type'], string>> = {
            queue: '/queue',
            document: '/documents',
            report: '/reports',
            registration: '/residents?tab=verifications',
        };
        const route = routes[notification.notification_type];
        if (route) navigate(route);
    };

    // 3. Action Logic: Delete
    const handleDelete = async () => {
        try {
            const idsToDelete = selectedIds.length === 0 ? notifications.map(n => n.id) : selectedIds;
            await Promise.all(
                idsToDelete.map(id => axiosPrivate.delete(`/admin-notifications/${id}/`))
            );
            setNotifications(prev => prev.filter(n => !idsToDelete.includes(n.id)));
            setSelectedIds([]);
            window.dispatchEvent(new Event('gridy:admin-notifications-changed'));
            toast.success("Notification(s) deleted.");
        } catch (err) {
            console.error("Failed to delete notifications:", err);
            toast.error("Failed to delete notifications.");
        }
    };

    // Helper to format ISO timestamp into readable time
    const formatTime = (isoString: string) => {
        try {
            const date = new Date(isoString);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' - ' + date.toLocaleDateString();
        } catch {
            return isoString;
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-6 pb-12">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-extrabold text-[#0f172a] tracking-tight">Notifications Center</h1>
                    <p className="text-[#64748b] text-sm mt-1">Stay updated on queue spikes, document requests, and system alerts.</p>
                </div>
                
                <div className="flex items-center gap-3">
                    <button 
                        onClick={handleMarkAsRead}
                        disabled={notifications.length === 0}
                        className="flex items-center gap-2 text-sm font-semibold text-primary-text hover:text-primary-text bg-primary/10 hover:bg-primary/15 px-4 py-2 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Check className="w-4 h-4" />
                        {selectedIds.length > 0 ? `Mark (${selectedIds.length}) as read` : 'Mark all as read'}
                    </button>
                    <button 
                        onClick={handleDelete}
                        disabled={notifications.length === 0}
                        className="flex items-center gap-2 text-sm font-semibold text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 px-4 py-2 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Trash2 className="w-4 h-4" />
                        {selectedIds.length > 0 ? `Delete (${selectedIds.length})` : 'Clear all'}
                    </button>
                </div>
            </div>
            
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                
                {/* Bulk Selection Header */}
                {notifications.length > 0 && (
                    <div className="flex items-center gap-3 p-4 border-b border-slate-100 bg-slate-50/50">
                        <button onClick={handleSelectAll} className="text-slate-400 hover:text-primary-text transition-colors">
                            {selectedIds.length === notifications.length ? (
                                <CheckSquare className="w-5 h-5 text-primary-text" />
                            ) : (
                                <Square className="w-5 h-5" />
                            )}
                        </button>
                        <span className="text-sm font-bold text-slate-700">Select All</span>
                    </div>
                )}

                {loading ? (
                    <div className="p-16 flex flex-col items-center justify-center text-slate-400">
                        <Loader2 className="w-8 h-8 animate-spin mb-2" />
                        <span>Loading notifications...</span>
                    </div>
                ) : loadError ? (
                    <InlineErrorState
                        message="We couldn't load notifications."
                        onRetry={() => void fetchNotifications(true)}
                        retrying={retrying}
                    />
                ) : (
                    <div className="divide-y divide-slate-100">
                        {notifications.map((notif) => {
                            const config = TYPE_CONFIG[notif.notification_type] || TYPE_CONFIG.system;
                            const Icon = config.icon;
                            const isSelected = selectedIds.includes(notif.id);
                            
                            return (
                                <div 
                                    key={notif.id} 
                                    className={`p-4 flex items-start gap-4 transition-colors hover:bg-slate-50 cursor-pointer ${!notif.is_read ? 'bg-primary/5' : ''} ${isSelected ? 'bg-primary/10' : ''}`}
                                    onClick={() => toggleSelection(notif.id)}
                                >
                                    {/* Checkbox */}
                                    <div className="mt-2.5">
                                        {isSelected ? (
                                            <CheckSquare className="w-5 h-5 text-primary-text" />
                                        ) : (
                                            <Square className="w-5 h-5 text-slate-300" />
                                        )}
                                    </div>

                                    {/* Icon */}
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${config.bg} ${config.color}`}>
                                        <Icon className="w-5 h-5" />
                                    </div>
                                    
                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between gap-2 mb-1">
                                            <h3 className={`text-sm font-bold truncate ${!notif.is_read ? 'text-slate-900' : 'text-slate-700'}`}>
                                                {notif.title}
                                            </h3>
                                            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 shrink-0">
                                                <Clock className="w-3.5 h-3.5" />
                                                {formatTime(notif.created_at)}
                                            </div>
                                        </div>
                                        <p className="text-sm text-slate-500 leading-relaxed">
                                            {notif.message}
                                        </p>
                                        {notif.notification_type !== 'system' && notif.notification_type !== 'alert' && (
                                            <button
                                                type="button"
                                                onClick={(event) => {
                                                    event.stopPropagation();
                                                    void openNotification(notif);
                                                }}
                                                className="mt-2 inline-flex min-h-9 items-center gap-1 rounded-lg px-2 text-xs font-bold text-primary-text hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                                            >
                                                Open related page <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                                            </button>
                                        )}
                                    </div>
                                    
                                    {/* Unread Indicator Dot */}
                                    {!notif.is_read && (
                                        <div className="w-2.5 h-2.5 bg-primary rounded-full shrink-0 mt-1.5"></div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
                
                {!loading && !loadError && notifications.length === 0 && (
                    <div className="p-16 text-center flex flex-col items-center">
                        <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mb-6">
                            <Bell className="w-10 h-10 text-slate-300" />
                        </div>
                        <h3 className="text-xl text-slate-900 font-bold mb-2">You're all caught up!</h3>
                        <p className="text-slate-500 text-sm max-w-md mx-auto leading-relaxed">
                            There are no new notifications at this time.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};
