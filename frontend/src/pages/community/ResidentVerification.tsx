import toast from 'react-hot-toast';
import { useCallback, useState, useEffect, useMemo, useRef } from "react";
import { axiosPrivate } from "../../api/axios";
import { Clock, Search, Filter } from "lucide-react";
import { InlineErrorState } from "../../components/ui/InlineErrorState";
import {
    formatPurok,
    type Resident,
    VerificationTable,
    VerificationDossierModal,
    RejectionConfirmationModal
} from "../../components/residents";

export default function ResidentVerification() {
    const [pendingResidents, setPendingResidents] = useState<Resident[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [retrying, setRetrying] = useState(false);
    const pendingRequestRef = useRef(false);
    
    // Search and Filter State
    const [searchQuery, setSearchQuery] = useState("");
    const [filterPurok, setFilterPurok] = useState("All");
    
    // Inspection and Rejection Modals
    const [residentToInspect, setResidentToInspect] = useState<Resident | null>(null);
    const [residentToReject, setResidentToReject] = useState<Resident | null>(null);
    const [rejectionReason, setRejectionReason] = useState('');
    const [isRejecting, setIsRejecting] = useState(false);

    const availablePuroks = useMemo(() => {
        const puroks = pendingResidents
            .map(r => r.purok)
            .filter((p): p is string => p !== null && p !== undefined);
        return ["All", ...new Set(puroks)].sort();
    }, [pendingResidents]);

    const filteredResidents = useMemo(() => {
        return pendingResidents.filter(resident => {
            const matchesSearch = resident.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (resident.philsys_id_number && resident.philsys_id_number.includes(searchQuery));
            const matchesPurok = filterPurok === "All" || resident.purok === filterPurok;
            return matchesSearch && matchesPurok;
        });
    }, [pendingResidents, searchQuery, filterPurok]);

    const fetchPendingResidents = useCallback(async (isRetry = false) => {
        if (pendingRequestRef.current) return;
        pendingRequestRef.current = true;

        if (isRetry) setRetrying(true);
        try {
            const response = await axiosPrivate.get('auth/pending-residents/');
            setPendingResidents(response.data.results || response.data);
            setLoadError(false);
        } catch (error) {
            console.error("Failed to fetch residents", error);
            setLoadError(true);
        } finally {
            pendingRequestRef.current = false;
            setLoading(false);
            setRetrying(false);
        }
    }, []);

    useEffect(() => {
        void fetchPendingResidents();
    }, [fetchPendingResidents]);

    useEffect(() => {
        const refreshWhenVisible = () => {
            if (document.visibilityState === 'visible') {
                void fetchPendingResidents(true);
            }
        };

        window.addEventListener('focus', refreshWhenVisible);
        document.addEventListener('visibilitychange', refreshWhenVisible);
        return () => {
            window.removeEventListener('focus', refreshWhenVisible);
            document.removeEventListener('visibilitychange', refreshWhenVisible);
        };
    }, [fetchPendingResidents]);

    const handleApprove = async (id: number) => {
        try {
            await axiosPrivate.patch(`auth/verify-resident/${id}/`);
            setPendingResidents((prev) => prev.filter((r) => r.id !== id));
            if (residentToInspect?.id === id) {
                setResidentToInspect(null);
            }
            toast.success('Resident successfully verified.');
        } catch (error) {
            console.error("Failed to verify resident", error);
            toast.error('Error verifying resident.');
        }
    };

    const handleReject = async () => {
        if (!residentToReject || isRejecting) return;

        const reason = rejectionReason.trim();
        if (!reason) {
            toast.error('Enter a reason for rejecting this resident.');
            return;
        }

        setIsRejecting(true);
        try {
            await axiosPrivate.delete(
                `auth/reject-resident/${residentToReject.id}/`,
                { data: { rejection_reason: reason } },
            );
            setPendingResidents((prev) => prev.filter((r) => r.id !== residentToReject.id));
            if (residentToInspect?.id === residentToReject.id) {
                setResidentToInspect(null);
            }
            setResidentToReject(null);
            setRejectionReason('');
            toast.success('Registration application rejected.');
        } catch (error) {
            console.error("Failed to reject resident", error);
            toast.error('Error rejecting resident.');
        } finally {
            setIsRejecting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-white rounded-xl shadow-sm border border-border overflow-hidden">
            {/* Header */}
            <div className="p-6 border-b border-border bg-surface flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-slate-800">Resident Verification</h1>
                    <p className="text-sm text-slate-500 mt-1">Review PhilSys national identity credentials and utility residency proofs.</p>
                </div>
                {!loadError && (
                    <div className="flex items-center gap-2">
                        <button
                            type="button"
                            aria-label="Refresh pending resident verifications"
                            onClick={() => { void fetchPendingResidents(true); }}
                            disabled={retrying}
                            className="inline-flex min-h-[44px] items-center justify-center rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-wait disabled:opacity-60"
                        >
                            {retrying ? 'Refreshing…' : 'Refresh'}
                        </button>
                        <div className="bg-amber-100 text-amber-800 px-4 py-2 rounded-full text-sm font-semibold flex items-center gap-2">
                            <Clock className="w-4 h-4" />
                            {filteredResidents.length} Pending Verification
                        </div>
                    </div>
                )}
            </div>

            {/* Search & Filter Bar */}
            <div className="p-4 bg-slate-50 border-b border-border flex flex-col sm:flex-row gap-4 items-center justify-between">
                <div className="relative w-full sm:w-96">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input 
                        type="text" 
                        placeholder="Search by name or PhilSys ID..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                    />
                </div>
                <div className="flex items-center gap-2 w-full sm:w-auto">
                    <Filter className="w-4 h-4 text-slate-400" />
                    <select 
                        aria-label="Filter residents by purok"
                        value={filterPurok}
                        onChange={(e) => setFilterPurok(e.target.value)}
                        className="w-full sm:w-auto px-4 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary cursor-pointer transition-all"
                    >
                        {availablePuroks.map(purok => (
                            <option key={purok} value={purok}>
                                {purok === "All" ? "All Puroks" : formatPurok(purok)}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Table */}
            {loadError ? (
                <div className="flex-1 overflow-auto p-6">
                    <InlineErrorState
                        message="We couldn't load pending resident verifications."
                        onRetry={() => { void fetchPendingResidents(true); }}
                        retrying={retrying}
                    />
                </div>
            ) : (
                <VerificationTable
                    residents={filteredResidents}
                    onInspect={setResidentToInspect}
                    onApprove={handleApprove}
                    onReject={(resident) => {
                        setRejectionReason('');
                        setResidentToReject(resident);
                    }}
                />
            )}

            {/* Verification Dossier / Inspection Modal */}
            {residentToInspect && (
                <VerificationDossierModal
                    resident={residentToInspect}
                    onClose={() => setResidentToInspect(null)}
                    onApprove={handleApprove}
                    onReject={(resident) => {
                        setResidentToInspect(null);
                        setRejectionReason('');
                        setResidentToReject(resident);
                    }}
                />
            )}

            {/* Rejection Confirmation Modal */}
            {residentToReject && (
                <RejectionConfirmationModal
                    resident={residentToReject}
                    rejectionReason={rejectionReason}
                    onReasonChange={setRejectionReason}
                    onConfirm={handleReject}
                    onCancel={() => {
                        setResidentToReject(null);
                        setRejectionReason('');
                    }}
                    isRejecting={isRejecting}
                />
            )}
        </div>
    );
}
