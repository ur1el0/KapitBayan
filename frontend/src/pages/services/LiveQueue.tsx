import React, { useEffect, useState, useMemo } from 'react';
import { axiosPrivate } from '../../api/axios';
import { getSafeApiErrorMessage } from '../../api/error-message';
import toast from 'react-hot-toast';
import { History, Plus, X, Volume2, VolumeX } from 'lucide-react';
import { InlineErrorState } from '../../components/ui/InlineErrorState';

import { QueueMetrics } from '../../components/queue/QueueMetrics';
import { ActiveTicketView } from '../../components/queue/ActiveTicketView';
import { WaitingListTable } from '../../components/queue/WaitingListTable';
import { NewTicketModal } from '../../components/queue/NewTicketModal';
import { QueueActionControls } from '../../components/queue/QueueActionControls';
import { QueueHistoryModal } from '../../components/queue/QueueHistoryModal';
import type { QueueTicket } from '../../components/queue/types';
import { useAuth } from '../../context/auth-context';

export const LiveQueue: React.FC = () => {
    const { user } = useAuth();
    const canManagePriority = user?.role === 'ADMIN';
    const [tickets, setTickets] = useState<QueueTicket[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string>('');
    const [hasLoadedQueue, setHasLoadedQueue] = useState(false);
    const [retrying, setRetrying] = useState(false);
    const [isUpdating, setIsUpdating] = useState<boolean>(false);

    // Modals & Form state
    const [isManualModalOpen, setIsManualModalOpen] = useState<boolean>(false);
    const [isHistoryModalOpen, setIsHistoryModalOpen] = useState<boolean>(false);
    const [searchResident, setSearchResident] = useState<string>('');
    const [serviceRequired, setServiceRequired] = useState<string>('');
    const [priorityStatus, setPriorityStatus] = useState<'regular' | 'priority'>('regular');
    const [priorityReason, setPriorityReason] = useState('');
    const [notes, setNotes] = useState<string>('');
    const [isSubmittingNew, setIsSubmittingNew] = useState<boolean>(false);
    
    // Phase 51: Auditory Live Queue
    const [audioEnabled, setAudioEnabled] = useState(false);
    const audioEnabledRef = React.useRef(false);
    const audioContextRef = React.useRef<AudioContext | null>(null);
    const previousTicketRef = React.useRef<string | null>(null);
    const hasLoadedQueueRef = React.useRef(false);

    const playChime = React.useCallback(async () => {
        if (!audioEnabledRef.current || typeof window.AudioContext === 'undefined') return;
        try {
            const context = audioContextRef.current ?? new window.AudioContext();
            audioContextRef.current = context;
            if (context.state === 'suspended') await context.resume();
            if (!audioEnabledRef.current) return;

            const oscillator = context.createOscillator();
            const gain = context.createGain();
            const now = context.currentTime;

            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(880, now);
            oscillator.frequency.setValueAtTime(1174.66, now + 0.12);

            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(0.18, now + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.35);

            oscillator.connect(gain);
            gain.connect(context.destination);
            oscillator.start();
            oscillator.stop(now + 0.36);
        } catch {}
    }, []);

    const announceTicket = React.useCallback((ticketNumber: string) => {
        if (!audioEnabledRef.current) return;
        void playChime();
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const announcement = new SpeechSynthesisUtterance(`Now serving ticket ${ticketNumber}. Please proceed to the service counter.`);
            announcement.lang = 'en-PH';
            announcement.rate = 0.95;
            window.speechSynthesis.speak(announcement);
        }
    }, [playChime]);
    const [notificationBanner, setNotificationBanner] = useState<string | null>(null);

    // Fetch tickets from backend
    const fetchTickets = React.useCallback(async (isRetry = false) => {
        if (isRetry) setRetrying(true);
        try {
            const response = await axiosPrivate.get('/tickets/');
            const newTickets = response.data.results || response.data || [];
            
            // Phase 51: Detect Serving Ticket change
            const newServing = newTickets.find((t: any) => t.status.toUpperCase() === 'SERVING');
            const newServingId = newServing ? newServing.ticket_number : null;
            
            if (
                hasLoadedQueueRef.current &&
                newServingId &&
                newServingId !== previousTicketRef.current
            ) {
                announceTicket(newServingId);
            }
            previousTicketRef.current = newServingId;
            hasLoadedQueueRef.current = true;
            
            setTickets(newTickets);
            setHasLoadedQueue(true);
            setError('');
        } catch (err) {
            console.error('Failed to load queue tickets:', err);
            setError('Failed to load queue tickets.');
        } finally {
            setLoading(false);
            if (isRetry) setRetrying(false);
        }
    }, [announceTicket]);

    useEffect(() => {
        fetchTickets();
        // Auto-poll live queue updates every 3 seconds
        const interval = setInterval(fetchTickets, 3000);
        return () => clearInterval(interval);
    }, [fetchTickets]);
    
    // Filtered lists
    const servingTicket = useMemo(() => {
        return tickets.find((t) => t.status.toUpperCase() === 'SERVING') || null;
    }, [tickets]);

    const waitingTickets = useMemo(() => {
        return tickets.filter((t) => t.status.toUpperCase() === 'WAITING');
    }, [tickets]);

    const completedTodayTickets = useMemo(() => {
        const todayStr = new Date().toDateString();
        return tickets.filter((t) => {
            const statusUpper = t.status.toUpperCase();
            const isCompleted = statusUpper === 'COMPLETED' || statusUpper === 'RESOLVED';
            const completionTime = t.updated_at || t.created_at;
            const isToday = new Date(completionTime).toDateString() === todayStr;
            return isCompleted && isToday;
        });
    }, [tickets]);

    // Dynamic calculations
    const totalWaitingCount = waitingTickets.length;
    const avgWaitMinutes = totalWaitingCount > 0 ? totalWaitingCount * 2 : 0;
    const servedTodayCount = completedTodayTickets.length;

    // Peak Hour calculation based on ticket creation times
    const peakHourText = useMemo(() => {
        if (tickets.length === 0) return '--';
        const hoursCount: { [hour: number]: number } = {};
        tickets.forEach((t) => {
            const d = new Date(t.created_at);
            if (!isNaN(d.getTime())) {
                const hour = d.getHours();
                hoursCount[hour] = (hoursCount[hour] || 0) + 1;
            }
        });
        const entries = Object.entries(hoursCount);
        if (entries.length === 0) return '--';
        entries.sort((a, b) => b[1] - a[1]);
        const topHour = parseInt(entries[0][0], 10);
        const period = topHour >= 12 ? 'PM' : 'AM';
        const displayHour = topHour % 12 === 0 ? 12 : topHour % 12;
        return `${displayHour}:00 ${period}`;
    }, [tickets]);

    // Handle Call Next / Advance Queue
    const handleNextQueue = async () => {
        if (waitingTickets.length === 0) return;
        setIsUpdating(true);
        try {
            const response = await axiosPrivate.post('/tickets/next/');
            await fetchTickets();
            showNotification(`Now serving ticket ${response.data.current_ticket}`);
        } catch (err) {
            console.error('Failed to advance queue:', err);
            toast.error('Failed to advance queue.');
        } finally {
            setIsUpdating(false);
        }
    };

    // Handle Mark Current as Done
    const handleMarkAsDone = async () => {
        if (!servingTicket) return;
        setIsUpdating(true);
        try {
            await axiosPrivate.post(`/tickets/${servingTicket.ticket_id}/complete/`);
            await fetchTickets();
            showNotification(`Ticket ${servingTicket.ticket_number} marked as completed.`);
        } catch (err) {
            console.error('Failed to complete ticket:', err);
            toast.error('Failed to complete ticket.');
        } finally {
            setIsUpdating(false);
        }
    };

    const handleNotifyResident = async () => {
        if (!servingTicket) return;
        setIsUpdating(true);
        try {
            const response = await axiosPrivate.post(
                `/tickets/${servingTicket.ticket_id}/notify/`,
            );
            toast.success(
                response.data.detail || 'Paging notification accepted for delivery.',
            );
        } catch (err) {
            toast.error(
                getSafeApiErrorMessage(
                    err,
                    'Could not page the resident. Please try again.',
                ),
            );
        } finally {
            setIsUpdating(false);
        }
    };

    // Handle Cancel Ticket
    const handleCancelTicket = async (ticketId: number) => {
        if (!window.confirm('Are you sure you want to cancel this ticket?')) return;
        setIsUpdating(true);
        try {
            await axiosPrivate.post(`/tickets/${ticketId}/cancel/`);
            await fetchTickets();
            toast.success('Queue ticket cancelled.');
        } catch (err) {
            toast.error(getSafeApiErrorMessage(
                err,
                "We couldn't cancel this queue ticket. Check your connection and try again.",
            ));
        } finally {
            setIsUpdating(false);
        }
    };

    const handlePriorityChange = async (
        ticketId: number,
        nextPriorityStatus: 'regular' | 'priority',
        reason: string,
    ): Promise<boolean> => {
        setIsUpdating(true);
        try {
            await axiosPrivate.post(`/tickets/${ticketId}/priority/`, {
                priority_status: nextPriorityStatus,
                reason,
            });
            await fetchTickets();
            toast.success(
                nextPriorityStatus === 'priority'
                    ? 'Priority status granted.'
                    : 'Priority status removed.',
            );
            return true;
        } catch (err: any) {
            const responseData = err.response?.data;
            const fieldMessage = err.response?.status < 500 ? responseData?.reason?.[0] : undefined;
            const message = fieldMessage || getSafeApiErrorMessage(
                err,
                "We couldn't update priority status. Check your connection and try again.",
            );
            toast.error(message);
            return false;
        } finally {
            setIsUpdating(false);
        }
    };

    const handleDeleteTicket = async (ticketId: number) => {
        if (!window.confirm("Are you sure you want to permanently delete this queue record?")) return;
        try {
            await axiosPrivate.delete(`/tickets/${ticketId}/`);
            setTickets(prev => prev.filter(t => t.ticket_id !== ticketId));
            toast.success('Queue record deleted successfully.');
        } catch (err) {
            console.error(err);
            toast.error('Failed to delete queue record.');
        }
    };

    // Create Manual Ticket
    const handleCreateManualTicket = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!serviceRequired) {
            toast.error('Please select a service category.');
            return;
        }
        setIsSubmittingNew(true);
        try {
            await axiosPrivate.post('/tickets/', {
                walkin_name: searchResident,
                service_type: serviceRequired,
                priority_status: priorityStatus,
                is_priority: priorityStatus === 'priority',
                ...(priorityStatus === 'priority'
                    ? { priority_reason: priorityReason.trim() }
                    : {}),
                notes: notes,
                status: 'WAITING',
            });

            await fetchTickets();
            setIsManualModalOpen(false);
            setSearchResident('');
            setServiceRequired('');
            setPriorityStatus('regular');
            setPriorityReason('');
            setNotes('');
            showNotification('New queue ticket issued successfully.');
        } catch (err) {
            console.error('Failed to create ticket:', err);
            toast.error('Failed to create manual ticket.');
        } finally {
            setIsSubmittingNew(false);
        }
    };

    const handleCloseManualModal = () => {
        setIsManualModalOpen(false);
        setSearchResident('');
        setServiceRequired('');
        setPriorityStatus('regular');
        setPriorityReason('');
        setNotes('');
    };

    const showNotification = (msg: string) => {
        setNotificationBanner(msg);
        setTimeout(() => {
            setNotificationBanner(null);
        }, 4000);
    };

    const handleAudioToggle = () => {
        const nextState = !audioEnabled;
        setAudioEnabled(nextState);
        audioEnabledRef.current = nextState;

        if (!nextState) {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel();
            }
            return;
        }

        try {
            if (typeof window.AudioContext !== 'undefined') {
                const context = audioContextRef.current ?? new window.AudioContext();
                audioContextRef.current = context;
                if (context.state === 'suspended') {
                    void context.resume().catch((error: unknown) => {
                        console.warn('Unable to resume queue audio:', error);
                    });
                }
            }

            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel();
                const confirmation = new SpeechSynthesisUtterance(
                    'Audio announcements enabled.',
                );
                confirmation.lang = 'en-US';
                window.speechSynthesis.speak(confirmation);
            }
        } catch (error) {
            console.warn('Unable to initialize queue audio:', error);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header / Title Section */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl lg:text-[28px] font-extrabold text-[#0f172a] tracking-tight">
                        Live Queue Management
                    </h1>
                    <p className="text-[#64748b] text-sm mt-1">
                        Real-time oversight of Barangay front-line services.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={handleAudioToggle}
                        className={`bg-white hover:bg-slate-50 border border-slate-200 px-4 py-2.5 rounded-xl text-sm font-semibold shadow-xs flex items-center gap-2 transition-all cursor-pointer ${
                            audioEnabled ? 'text-primary' : 'text-slate-700'
                        }`}
                        title={audioEnabled ? 'Mute Announcer' : 'Enable Announcer'}
                    >
                        {audioEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4 text-slate-500" />}
                        <span className="hidden sm:inline">{audioEnabled ? 'Audio On' : 'Audio Off'}</span>
                    </button>

                    <button
                        onClick={() => setIsHistoryModalOpen(true)}
                        className="bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 px-4 py-2.5 rounded-xl text-sm font-semibold shadow-xs flex items-center gap-2 transition-all cursor-pointer"
                    >
                        <History className="w-4 h-4 text-slate-500" />
                        <span>Queue History</span>
                    </button>

                    <button
                        onClick={() => setIsManualModalOpen(true)}
                        className="bg-primary hover:bg-primary-hover active:bg-primary-hover text-primary-foreground px-5 py-2.5 rounded-xl text-sm font-semibold shadow-sm flex items-center gap-2 transition-all cursor-pointer"
                    >
                        <Plus className="w-4 h-4 stroke-[3]" />
                        <span>Manual Entry</span>
                    </button>
                </div>
            </div>

            {/* Notification Toast */}
            {notificationBanner && (
                <div className="bg-primary/10 border border-primary/30 text-primary-text px-4 py-3 rounded-xl text-sm font-semibold flex items-center justify-between shadow-sm animate-fade-in">
                    <span>{notificationBanner}</span>
                    <button onClick={() => setNotificationBanner(null)} className="text-primary-text hover:opacity-80">
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            {error && hasLoadedQueue && (
                <div role="alert" className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm font-medium">
                    {error}
                </div>
            )}

            {/* Main Top Grid (Now Serving + 4 Stat Cards) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                <div className="lg:col-span-5">
                    {hasLoadedQueue ? (
                        <ActiveTicketView servingTicket={servingTicket} />
                    ) : error ? (
                        <InlineErrorState
                            message="Failed to load queue tickets."
                            onRetry={() => { void fetchTickets(true); }}
                            retrying={retrying}
                        />
                    ) : (
                        <p role="status" className="rounded-xl bg-surface p-6 text-sm text-neutral-secondary">
                            Loading queue tickets…
                        </p>
                    )}
                </div>
                <div className="lg:col-span-7">
                    <QueueMetrics 
                        loading={loading || !hasLoadedQueue}
                        totalWaitingCount={totalWaitingCount}
                        avgWaitMinutes={avgWaitMinutes}
                        servedTodayCount={servedTodayCount}
                        peakHourText={peakHourText}
                    />
                </div>
            </div>

            {/* Action Control Bar (Middle Row) */}
            <QueueActionControls
                isUpdating={isUpdating}
                waitingCount={waitingTickets.length}
                servingTicket={servingTicket}
                onNextQueue={handleNextQueue}
                onMarkAsDone={handleMarkAsDone}
                onNotifyResident={handleNotifyResident}
            />
            
            {/* Bottom Section: Waiting List Table */}
            {hasLoadedQueue && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                    <div className="lg:col-span-12">
                        <WaitingListTable
                            waitingTickets={waitingTickets}
                            isUpdating={isUpdating}
                            fetchTickets={fetchTickets}
                            canManagePriority={canManagePriority}
                            handlePriorityChange={handlePriorityChange}
                            handleCancelTicket={handleCancelTicket}
                        />
                    </div>
                </div>
            )}

            {isManualModalOpen && (
                <NewTicketModal 
                    handleCloseManualModal={handleCloseManualModal}
                    handleCreateManualTicket={handleCreateManualTicket}
                    searchResident={searchResident}
                    setSearchResident={setSearchResident}
                    serviceRequired={serviceRequired}
                    setServiceRequired={setServiceRequired}
                    canManagePriority={canManagePriority}
                    priorityStatus={priorityStatus}
                    setPriorityStatus={setPriorityStatus}
                    priorityReason={priorityReason}
                    setPriorityReason={setPriorityReason}
                    notes={notes}
                    setNotes={setNotes}
                    isSubmittingNew={isSubmittingNew}
                />
            )}

            {/* Modal: Queue History */}
            <QueueHistoryModal
                isOpen={isHistoryModalOpen}
                onClose={() => setIsHistoryModalOpen(false)}
                tickets={tickets}
                onDeleteTicket={handleDeleteTicket}
            />
        </div>
    );
};
