import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ResidentsManagement } from './ResidentsManagement';
import ResidentVerification from './ResidentVerification';
import { axiosPrivate } from '../../api/axios';
import { Users, UserCheck } from 'lucide-react';

export const ResidentsHub: React.FC = () => {
    const [searchParams, setSearchParams] = useSearchParams();
    const tabParam = searchParams.get('tab');
    const [activeTab, setActiveTab] = useState<'directory' | 'verifications'>(
        tabParam === 'verifications' ? 'verifications' : 'directory'
    );
    const [pendingCount, setPendingCount] = useState<number | null>(null);
    const [pendingCountStatus, setPendingCountStatus] = useState<'idle' | 'loading' | 'error' | 'success'>('idle');
    const [retryingPendingCount, setRetryingPendingCount] = useState(false);
    const pendingCountRequestId = useRef(0);
    const pendingCountFetchInProgress = useRef(false);

    // Sync tab state when URL search param changes
    useEffect(() => {
        if (tabParam === 'verifications') {
            setActiveTab('verifications');
        } else if (tabParam === 'directory') {
            setActiveTab('directory');
        }
    }, [tabParam]);

    const fetchPendingCount = useCallback(async (showLoading = false, isRetry = false) => {
        if (pendingCountFetchInProgress.current) {
            if (showLoading && !isRetry) setPendingCountStatus('loading');
            return;
        }
        pendingCountFetchInProgress.current = true;
        const requestId = ++pendingCountRequestId.current;
        if (isRetry) {
            setRetryingPendingCount(true);
        } else {
            setRetryingPendingCount(false);
            if (showLoading) {
                setPendingCountStatus('loading');
            }
        }

        try {
            const res = await axiosPrivate.get('/auth/pending-residents/');
            const residents = Array.isArray(res.data) ? res.data : res.data?.results;
            if (!Array.isArray(residents)) {
                throw new Error('Unexpected pending residents response');
            }
            if (requestId !== pendingCountRequestId.current) return;
            setPendingCount(residents.length);
            setPendingCountStatus('success');
        } catch (err) {
            if (requestId !== pendingCountRequestId.current) return;
            console.error('Failed to fetch pending verifications count:', err);
            setPendingCountStatus('error');
        } finally {
            pendingCountFetchInProgress.current = false;
            if (requestId === pendingCountRequestId.current) {
                setRetryingPendingCount(false);
            }
        }
    }, []);

    useEffect(() => {
        void fetchPendingCount();
        const refreshWhenVisible = () => {
            if (document.visibilityState === 'visible') {
                void fetchPendingCount();
            }
        };
        const intervalId = window.setInterval(refreshWhenVisible, 3000);
        document.addEventListener('visibilitychange', refreshWhenVisible);
        window.addEventListener('focus', refreshWhenVisible);

        return () => {
            window.clearInterval(intervalId);
            document.removeEventListener('visibilitychange', refreshWhenVisible);
            window.removeEventListener('focus', refreshWhenVisible);
            pendingCountRequestId.current += 1;
        };
    }, [fetchPendingCount]);

    const handleTabChange = (tab: 'directory' | 'verifications') => {
        setActiveTab(tab);
        setSearchParams((current) => {
            const next = new URLSearchParams(current);
            next.set('tab', tab);
            return next;
        });
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            <div>
                <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Residents & Community Center</h2>
                <p className="text-sm text-slate-600 mt-1">
                    Manage the official resident registry, review PhilSys verifications, and import census rosters.
                </p>
            </div>

            <div className="border-b border-slate-200 bg-white px-2 rounded-xl shadow-2xs">
                <nav className="-mb-px flex flex-wrap gap-x-3" aria-label="Resident views">
                    <button
                        type="button"
                        aria-pressed={activeTab === 'directory'}
                        onClick={() => handleTabChange('directory')}
                        className={`flex items-center gap-2 whitespace-nowrap py-4 px-2 border-b-2 font-medium text-sm transition-colors cursor-pointer ${
                            activeTab === 'directory'
                                ? 'border-primary text-primary-text font-bold'
                                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                        }`}
                    >
                        <Users className="w-4 h-4" />
                        <span>Residents Directory & RBI</span>
                    </button>

                    <button
                        type="button"
                        aria-pressed={activeTab === 'verifications'}
                        onClick={() => handleTabChange('verifications')}
                        className={`flex items-center gap-2 whitespace-nowrap py-4 px-2 border-b-2 font-medium text-sm transition-colors cursor-pointer ${
                            activeTab === 'verifications'
                                ? 'border-primary text-primary-text font-bold'
                                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                        }`}
                    >
                        <UserCheck className="w-4 h-4" />
                        <span>Resident Verifications</span>
                        {pendingCountStatus === 'success' && pendingCount !== null && pendingCount > 0 && (
                            <span
                                aria-label={`${pendingCount} pending resident verifications`}
                                className="ml-1.5 px-2 py-0.5 text-xs font-bold rounded-full bg-amber-100 text-amber-800"
                            >
                                {pendingCount}
                            </span>
                        )}
                    </button>
                </nav>
                {pendingCountStatus === 'loading' && (
                    <p role="status" aria-live="polite" className="px-2 pb-3 text-xs text-slate-500">
                        {retryingPendingCount ? 'Retrying pending resident count…' : 'Loading pending resident count…'}
                    </p>
                )}
                {pendingCountStatus === 'error' && (
                    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 px-2 pb-3 text-sm text-rose-700">
                        <p>Pending resident count couldn&apos;t be loaded.</p>
                        <button
                            type="button"
                            aria-label="Retry pending resident count"
                            onClick={() => void fetchPendingCount(true, true)}
                            disabled={retryingPendingCount}
                            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border border-rose-300 px-3 font-semibold text-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 disabled:cursor-wait disabled:opacity-60"
                        >
                            {retryingPendingCount ? 'Retrying…' : 'Retry pending resident count'}
                        </button>
                        {retryingPendingCount && (
                            <span role="status" aria-live="polite" className="sr-only">
                                Retrying pending resident count…
                            </span>
                        )}
                    </div>
                )}
            </div>

            <div className="mt-4">
                {activeTab === 'directory' ? (
                    <ResidentsManagement />
                ) : (
                    <ResidentVerification onManualRefreshCount={() => void fetchPendingCount(true)} />
                )}
            </div>
        </div>
    );
};
