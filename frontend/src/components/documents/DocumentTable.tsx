import { Trash2 } from 'lucide-react';
import { InlineErrorState } from '../ui/InlineErrorState';
import type { DocumentRequest } from '../../pages/services/DocumentRequests';

interface DocumentTableProps {
    requests: DocumentRequest[];
    openModal: (request: DocumentRequest) => void;
    getStatusBadge: (status: string) => string;
    onDelete?: (id: number) => void;
    loadError?: { message: string; onRetry: () => void; retrying: boolean };
}

export const DocumentTable = ({ requests, openModal, getStatusBadge, onDelete, loadError }: DocumentTableProps) => {
    return (
        <div className="bg-white shadow-sm border border-slate-200 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50">
                        <tr>
                            <th scope="col" className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">ID</th>
                            <th scope="col" className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Applicant</th>
                            <th scope="col" className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Purok</th>
                            <th scope="col" className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Clearance Type</th>
                            <th scope="col" className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Requested Speed</th>
                            <th scope="col" className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">O.R. No.</th>
                            <th scope="col" className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
                            <th scope="col" className="px-6 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-slate-100">
                        {loadError && (
                            <tr>
                                <td colSpan={8} className="px-4 py-4">
                                    <InlineErrorState
                                        message={loadError.message}
                                        onRetry={loadError.onRetry}
                                        retrying={loadError.retrying}
                                    />
                                </td>
                            </tr>
                        )}
                        {!loadError && requests.length === 0 ? (
                            <tr>
                                <td colSpan={8} className="px-6 py-12 text-center text-sm text-slate-500">
                                    No clearance requests recorded yet.
                                </td>
                            </tr>
                        ) : (
                            requests.map((req, index) => (
                                <tr 
                                    key={req.id || index} 
                                    onClick={() => openModal(req)} 
                                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                                >
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-slate-900">
                                        #{req.id}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold text-slate-900">
                                                {req.requester_name || req.walkin_name || 'Resident'}
                                            </span>
                                            {req.is_walkin && (
                                                <span className="px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wide bg-amber-100 text-amber-800 rounded-md border border-amber-200">
                                                    Walk-in
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                                        {req.purok || req.walkin_purok || 'N/A'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-800 font-medium">
                                        {req.document_type}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {req.urgency_tag === 'URGENT' ? (
                                            <span className="inline-flex rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-800">
                                                Urgent (requested)
                                            </span>
                                        ) : (
                                            <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600">
                                                Regular
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 font-mono">
                                        {req.or_number ? req.or_number : <span className="text-slate-400 italic">None</span>}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                                        {new Date(req.created_at).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center gap-2">
                                            <span className={`px-2.5 py-1 inline-flex text-xs leading-5 font-bold rounded-full border ${getStatusBadge(req.status)}`}>
                                                {req.status.replace(/_/g, ' ')}
                                            </span>
                                            {onDelete && ['RELEASED', 'REJECTED'].includes(req.status) && (
                                                <button
                                                    type="button"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        onDelete(req.id);
                                                    }}
                                                    className="p-1 text-slate-400 hover:text-rose-600 rounded-md hover:bg-rose-50 transition-colors"
                                                    title="Delete clearance request"
                                                    aria-label={`Delete request #${req.id}`}
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
