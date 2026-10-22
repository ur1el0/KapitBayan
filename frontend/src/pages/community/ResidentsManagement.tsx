import toast from 'react-hot-toast';
import React, { useCallback, useEffect, useRef, useState } from "react";
import { axiosPrivate } from "../../api/axios";
import { getSafeApiErrorMessage } from "../../api/error-message";
import { Search, Upload } from "lucide-react";
import { InlineErrorState } from "../../components/ui/InlineErrorState";
import {
    type Resident,
    type ImportSummary,
    ResidentDirectoryTable,
    ResidentDetailModal,
    ResidentImportModal
} from "../../components/residents";

export const ResidentsManagement: React.FC = () => {
    const [residents, setResidents] = useState<Resident[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [retrying, setRetrying] = useState(false);
    const [search, setSearch] = useState('');
    const residentsFetchInProgress = useRef(false);

    // Detail Modal State
    const [selectedResident, setSelectedResident] = useState<Resident | null>(null);
    const [emailDraft, setEmailDraft] = useState("");
    const [savingEmail, setSavingEmail] = useState(false);

    // Import Modal State
    const [isImportModalOpen, setIsImportModalOpen] = useState(false);
    const [csvFile, setCsvFile] = useState<File | null>(null);
    const [importing, setImporting] = useState(false);
    const [importSummary, setImportSummary] = useState<ImportSummary | null>(null);

    const fetchResidents = useCallback(async (isRetry = false) => {
        if (residentsFetchInProgress.current) return;
        residentsFetchInProgress.current = true;
        if (isRetry) setRetrying(true);
        try {
            const response = await axiosPrivate.get('/auth/resident/');
            setResidents(response.data.results || response.data);
            setLoadError(false);
        } catch (err) {
            console.error("Failed to fetch directory:", err);
            setLoadError(true);
        } finally {
            residentsFetchInProgress.current = false;
            setLoading(false);
            setRetrying(false);
        }
    }, []);

    useEffect(() => {
        void fetchResidents();
        const refreshWhenVisible = () => {
            if (document.visibilityState === 'visible') {
                void fetchResidents();
            }
        };
        const intervalId = window.setInterval(refreshWhenVisible, 3000);
        document.addEventListener('visibilitychange', refreshWhenVisible);
        window.addEventListener('focus', refreshWhenVisible);

        return () => {
            window.clearInterval(intervalId);
            document.removeEventListener('visibilitychange', refreshWhenVisible);
            window.removeEventListener('focus', refreshWhenVisible);
        };
    }, [fetchResidents]);

    const handleDelete = async (id: number) => {
        if (!window.confirm("Are you sure you want to permanently remove this resident? This will revoke all their access.")) return;
        try {
            await axiosPrivate.delete(`/auth/resident/${id}/`);
            setResidents(prev => prev.filter(r => r.id !== id));
            if (selectedResident?.id === id) {
                setSelectedResident(null);
            }
            toast.success('Resident record deleted.');
        } catch (err) {
            console.error("Failed to delete resident", err);
            toast.error('Failed to delete resident.');
        }
    };

    const handleEmailSave = async () => {
        if (!selectedResident) return;

        const email = emailDraft.trim();
        if (!email) {
            toast.error("Enter the resident's email address.");
            return;
        }

        setSavingEmail(true);
        try {
            const response = await axiosPrivate.patch(
                `/auth/resident/${selectedResident.id}/`,
                { email },
            );

            const updatedResident = {
                ...selectedResident,
                email: response.data.email ?? email.toLowerCase(),
            };

            setSelectedResident((current) =>
                current?.id === updatedResident.id ? updatedResident : current,
            );
            setResidents((current) =>
                current.map((resident) =>
                    resident.id === updatedResident.id ? updatedResident : resident,
                ),
            );
            setEmailDraft(updatedResident.email ?? "");
            toast.success(
                "Email updated. The resident can use Forgot Password to set a password.",
            );
        } catch (error: any) {
            const errorData = error.response?.data;
            toast.error(
                errorData?.email?.[0] ??
                    errorData?.detail ??
                    "Failed to update resident email.",
            );
        } finally {
            setSavingEmail(false);
        }
    };

    const getAge = (birthDateStr: string) => {
        if (!birthDateStr) return 'N/A';
        const birth = new Date(birthDateStr);
        const today = new Date();
        let age = today.getFullYear() - birth.getFullYear();
        const m = today.getMonth() - birth.getMonth();
        if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
        return `${age} years old`;
    };

    const handleDownloadTemplate = () => {
        const header = "username,email,full_name,birth_date,contact_number,purok,voter_status,philsys_id_number\n";
        const sample1 = "juandelacruz,juan@example.com,Juan Dela Cruz,1990-05-15,09171234567,Purok 1,True,1234-5678-9012-3456\n";
        const sample2 = "mariasantos,,Maria Santos,1985-11-20,,Purok 2,False,\n";
        const csvContent = "data:text/csv;charset=utf-8," + header + sample1 + sample2;
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "barangay_rbi_template.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            if (!file.name.endsWith('.csv')) {
                toast.error('Please upload a valid .csv file.');
                return;
            }
            setCsvFile(file);
            setImportSummary(null);
        }
    };

    const handleImportSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!csvFile) {
            toast.error('Please select a CSV file to import.');
            return;
        }

        try {
            setImporting(true);
            const formData = new FormData();
            formData.append('file', csvFile);

            const res = await axiosPrivate.post('/auth/import-residents/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            setImportSummary(res.data);
            toast.success(`Successfully imported ${res.data.imported} resident records!`);
            fetchResidents();
        } catch (err: any) {
            const errorData = err.response?.data;
            if (!err.response || err.response.status >= 500) {
                toast.error(getSafeApiErrorMessage(
                    err,
                    "We couldn't import the resident records. Check your connection and try again.",
                ));
                return;
            }
            if (errorData && errorData.imported !== undefined) {
                setImportSummary(errorData);
                toast.error('Import completed with validation warnings.');
                fetchResidents();
            } else {
                toast.error(getSafeApiErrorMessage(err, 'Failed to import CSV file.'));
            }
        } finally {
            setImporting(false);
        }
    };

    const filteredResidents = residents.filter(r => 
        r.full_name.toLowerCase().includes(search.toLowerCase()) ||
        (r.username && r.username.toLowerCase().includes(search.toLowerCase())) ||
        (r.purok && String(r.purok).toLowerCase().includes(search.toLowerCase())) ||
        (r.philsys_id_number && r.philsys_id_number.toLowerCase().includes(search.toLowerCase()))
    );

    return (
        <div className="space-y-6">
            {/* Header and Controls */}
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
                <div>
                    <h3 className="text-lg font-bold text-slate-900">Residents Directory & RBI</h3>
                    <p className="text-xs text-slate-500 mt-0.5">Click any resident row to view their complete dossier and identification proofs.</p>
                </div>

                <div className="flex items-center gap-3 w-full lg:w-auto">
                    <label className="relative flex-1 lg:w-64">
                        <span className="sr-only">Search residents</span>
                        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search name, PhilSys ID, purok..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all shadow-2xs"
                        />
                    </label>

                    <button
                        onClick={() => {
                            setIsImportModalOpen(true);
                            setImportSummary(null);
                            setCsvFile(null);
                        }}
                        className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-primary-foreground rounded-xl text-sm font-bold shadow-xs transition-all cursor-pointer shrink-0 active:scale-95"
                    >
                        <Upload className="w-4 h-4" />
                        <span>Import CSV</span>
                    </button>
                </div>
            </div>

            {/* Resident Directory Table */}
            {loadError ? (
                <InlineErrorState
                    message="We couldn't load the resident directory."
                    onRetry={() => { void fetchResidents(true); }}
                    retrying={retrying}
                />
            ) : (
                <ResidentDirectoryTable
                    residents={filteredResidents}
                    loading={loading}
                    onSelectResident={(resident) => {
                        setSelectedResident(resident);
                        setEmailDraft(resident.email ?? "");
                    }}
                    onDeleteResident={handleDelete}
                    getAge={getAge}
                />
            )}

            {/* Resident Profile Inspection Modal */}
            {selectedResident && (
                <ResidentDetailModal
                    resident={selectedResident}
                    emailDraft={emailDraft}
                    setEmailDraft={setEmailDraft}
                    savingEmail={savingEmail}
                    onSaveEmail={handleEmailSave}
                    onClose={() => setSelectedResident(null)}
                    getAge={getAge}
                />
            )}

            {/* CSV Import Modal */}
            <ResidentImportModal
                isOpen={isImportModalOpen}
                onClose={() => setIsImportModalOpen(false)}
                csvFile={csvFile}
                onFileChange={handleFileChange}
                onDownloadTemplate={handleDownloadTemplate}
                onSubmit={handleImportSubmit}
                importing={importing}
                importSummary={importSummary}
            />
        </div>
    );
};
