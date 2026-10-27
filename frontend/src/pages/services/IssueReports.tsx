import React, { useCallback, useEffect, useState } from 'react';
import { axiosPrivate } from '../../api/axios';
import { InlineErrorState } from '../../components/ui/InlineErrorState';

interface IssueReport {
    id: number;
    title: string;
    description: string;
    location: string;
    image: string | null;
    status: string;
    urgency: string;
    created_at: string;
}

const TableSkeleton = () => (
    <div className="space-y-6 animate-pulse">
        <div className="flex justify-between items-center">
            <div className="h-8 w-40 bg-slate-200 rounded"></div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 h-12 border-b border-slate-200 w-full"></div>
            {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex h-16 border-b border-slate-100 items-center px-6 gap-4">
                    <div className="h-4 w-10 bg-slate-200 rounded"></div>
                    <div className="h-4 w-48 bg-slate-200 rounded"></div>
                    <div className="h-4 w-32 bg-slate-200 rounded"></div>
                    <div className="h-6 w-20 bg-slate-200 rounded-full"></div>
                    <div className="h-6 w-20 bg-slate-200 rounded-full"></div>
                </div>
            ))}
        </div>
    </div>
);

export const IssueReports: React.FC = () => {
    const [reports, setReports] = useState<IssueReport[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [retrying, setRetrying] = useState(false);

    const [selectedReport, setSelectedReport] = useState<IssueReport | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isUpdating, setIsUpdating] = useState(false);
    
    // Lightbox state for the image
    const [lightboxImage, setLightboxImage] = useState<string | null>(null);

    const fetchReports = useCallback(async (isRetry = false) => {
        if (isRetry) {
            setRetrying(true);
        } else {
            setLoading(true);
        }

        try {
            const response = await axiosPrivate.get('/reports/');
            setReports(response.data.results || response.data);
            setError('');
        } catch (err) {
            setError('Failed to load issue reports.');
            console.error(err);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    }, []);

    useEffect(() => {
        void fetchReports();
    }, [fetchReports]);

    const getStatusBadge = (status: string) => {
        switch (status.toUpperCase()) {
            case 'PENDING': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'IN_PROGRESS': return 'bg-blue-100 text-blue-800 border-blue-200';
            case 'RESOLVED': return 'bg-green-100 text-green-800 border-green-200';
            default: return 'bg-slate-100 text-slate-800 border-slate-200';
        }
    };

    const getUrgencyBadge = (urgency: string) => {
        switch (urgency.toUpperCase()) {
            case 'EMERGENCY': return 'bg-red-100 text-red-800 border-red-200';
            case 'URGENT': return 'bg-red-100 text-red-800 border-red-200';
            case 'HAZARD': return 'bg-orange-100 text-orange-800 border-orange-200';
            case 'HIGH': return 'bg-orange-100 text-orange-800 border-orange-200';
            case 'MODERATE': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'MEDIUM': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'MINOR': return 'bg-slate-100 text-slate-800 border-slate-200';
            case 'LOW': return 'bg-slate-100 text-slate-800 border-slate-200';
            default: return 'bg-slate-100 text-slate-800 border-slate-200';
        }
    };

    const openModal = (report: IssueReport) => {
        setSelectedReport(report);
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setSelectedReport(null);
    };

    const handleStatusUpdate = async (newStatus: string) => {
        if (!selectedReport) return;
        setIsUpdating(true);
        
        try {
            await axiosPrivate.patch(`/reports/${selectedReport.id}/`, {
                status: newStatus
            });
            
            setReports(prev => prev.map(rep => 
                rep.id === selectedReport.id ? { ...rep, status: newStatus } : rep
            ));
            
            closeModal();
        } catch (err) {
            console.error("Failed to update status", err);
            console.error("Failed to update status. Please try again.");
        } finally {
            setIsUpdating(false);
        }
    };

    if (loading) return <div className="p-4 md:p-8"><TableSkeleton /></div>;

    return (
        <div className="space-y-6 relative">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-slate-900">Issue Reports</h2>
            </div>

            <div className="bg-surface shadow-sm border border-border rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-border">
                    <thead className="bg-slate-50">
                        <tr>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">ID</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Title</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Location</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Urgency</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Date</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-border">
                        {error && (
                            <tr>
                                <td colSpan={6} className="px-4 py-4">
                                    <InlineErrorState
                                        message="We couldn't load issue reports."
                                        onRetry={() => void fetchReports(true)}
                                        retrying={retrying}
                                    />
                                </td>
                            </tr>
                        )}
                        {!error && reports.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-6 py-4 text-center text-sm text-slate-500">No issue reports found.</td>
                            </tr>
                        ) : (
                            reports.map((rep) => (
                                <tr key={rep.id} onClick={() => openModal(rep)} className="hover:bg-slate-50 transition-colors cursor-pointer">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900 font-medium">#{rep.id}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-700">{rep.title}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{rep.location}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full border ${getUrgencyBadge(rep.urgency)}`}>
                                            {rep.urgency}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full border ${getStatusBadge(rep.status)}`}>
                                            {rep.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                                        {new Date(rep.created_at).toLocaleDateString()}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {isModalOpen && selectedReport && (
                <div className="fixed inset-0 overflow-hidden z-40">
                    <div className="absolute inset-0 overflow-hidden">
                        <div className="absolute inset-0 bg-slate-900 bg-opacity-75 transition-opacity" onClick={closeModal} />
                        
                        <div className="fixed inset-y-0 right-0 max-w-md w-full flex">
                            <div className="w-full h-full bg-white shadow-xl flex flex-col">
                                
                                <div className="px-6 py-6 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                                    <h3 className="text-lg font-medium text-slate-900">Issue #{selectedReport.id} Details</h3>
                                    <button onClick={closeModal} className="text-slate-400 hover:text-slate-500">
                                        <span className="text-2xl">&times;</span>
                                    </button>
                                </div>

                                <div className="flex-1 px-6 py-6 space-y-6 overflow-y-auto">
                                    
                                    {selectedReport.image && (
                                        <div className="mb-4">
                                            <h4 className="text-sm font-medium text-slate-500 mb-2">Attached Image</h4>
                                            <div 
                                                className="relative h-48 w-full overflow-hidden rounded-lg border border-slate-200 cursor-pointer hover:opacity-90 transition-opacity"
                                                onClick={() => setLightboxImage(selectedReport.image)}
                                            >
                                                <img 
                                                    src={selectedReport.image} 
                                                    alt="Issue Attachment" 
                                                    className="w-full h-full object-cover"
                                                />
                                                <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 bg-black bg-opacity-30 transition-opacity">
                           <span className="text-white text-sm font-medium bg-black bg-opacity-50 px-3 py-1 rounded-full">
                             Click to Enlarge
                           </span>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    <div>
                                        <h4 className="text-sm font-medium text-slate-500">Title</h4>
                                        <p className="mt-1 text-sm text-slate-900 font-semibold">{selectedReport.title}</p>
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-medium text-slate-500">Description</h4>
                                        <p className="mt-1 text-sm text-slate-900 bg-slate-50 p-3 rounded-md border border-slate-200">{selectedReport.description}</p>
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-medium text-slate-500">Location</h4>
                                        <p className="mt-1 text-sm text-slate-900">{selectedReport.location}</p>
                                    </div>
                                    <div className="flex space-x-6">
                                        <div>
                                            <h4 className="text-sm font-medium text-slate-500 mb-2">Urgency</h4>
                                            <span className={`px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full border ${getUrgencyBadge(selectedReport.urgency)}`}>
                                                {selectedReport.urgency}
                                            </span>
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-medium text-slate-500 mb-2">Status</h4>
                                            <span className={`px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full border ${getStatusBadge(selectedReport.status)}`}>
                                                {selectedReport.status}
                                            </span>
                                        </div>
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-medium text-slate-500">Date Reported</h4>
                                        <p className="mt-1 text-sm text-slate-900">{new Date(selectedReport.created_at).toLocaleString()}</p>
                                    </div>
                                </div>

                                <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-end space-x-3">
                                    <button onClick={closeModal} className="px-4 py-2 border border-slate-300 rounded-md shadow-sm text-sm font-medium text-slate-700 bg-white hover:bg-slate-50">
                                        Close
                                    </button>
                                    
                                    {selectedReport.status.toUpperCase() === 'PENDING' && (
                                        <button 
                                            onClick={() => handleStatusUpdate('IN_PROGRESS')}
                                            disabled={isUpdating}
                                            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-primary-foreground bg-primary hover:bg-primary-hover disabled:opacity-50"
                                        >
                                            {isUpdating ? 'Updating...' : 'Mark In Progress'}
                                        </button>
                                    )}

                                    {selectedReport.status.toUpperCase() === 'IN_PROGRESS' && (
                                        <button 
                                            onClick={() => handleStatusUpdate('RESOLVED')}
                                            disabled={isUpdating}
                                            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                                        >
                                            {isUpdating ? 'Updating...' : 'Mark Resolved'}
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Lightbox Modal */}
            {lightboxImage && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-90" onClick={() => setLightboxImage(null)}>
                    <button 
                        className="absolute top-6 right-6 text-white hover:text-slate-300 text-4xl"
                        onClick={(e) => { e.stopPropagation(); setLightboxImage(null); }}
                    >
                        &times;
                    </button>
                    <img 
                        src={lightboxImage} 
                        alt="Expanded Issue Attachment" 
                        className="max-w-full max-h-full object-contain rounded-lg shadow-2xl cursor-default"
                        onClick={(e) => e.stopPropagation()} // Prevent clicks on the image from closing it
                    />
                </div>
            )}
        </div>
    );
};
