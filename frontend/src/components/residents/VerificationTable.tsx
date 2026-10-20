import React from 'react';
import {
    CheckCircle,
    XCircle,
    Eye,
    FileText,
    Receipt,
    IdCard
} from 'lucide-react';
import type { Resident } from './types';

interface VerificationTableProps {
    residents: Resident[];
    onInspect: (resident: Resident) => void;
    onApprove: (id: number) => void;
    onReject: (resident: Resident) => void;
}

export const VerificationTable: React.FC<VerificationTableProps> = ({
    residents,
    onInspect,
    onApprove,
    onReject,
}) => {
    return (
        <div className="flex-1 overflow-auto">
            <table className="w-full text-left border-collapse">
                <thead className="bg-[#F8FAFD] sticky top-0 z-10">
                    <tr>
                        <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-border">Applicant</th>
                        <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-border">PhilSys Number</th>
                        <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-border">Purok</th>
                        <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-border">Submitted Proofs</th>
                        <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-border text-right">Actions</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-border">
                    {residents.length === 0 ? (
                        <tr>
                            <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                                No pending verifications match your filters.
                            </td>
                        </tr>
                    ) : (
                        residents.map((resident) => (
                            <tr key={resident.id} className="hover:bg-slate-50 transition-colors">
                                <td className="px-6 py-4">
                                    <div className="font-semibold text-slate-800">{resident.full_name}</div>
                                    <div className="text-xs text-slate-500 mt-0.5">DOB: {resident.birth_date}</div>
                                    {resident.guardian && (
                                        <div className="mt-1 inline-flex items-center text-[11px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                                            Minor (Guardian: CID-{resident.guardian})
                                        </div>
                                    )}
                                </td>
                                <td className="px-6 py-4 text-sm">
                                    {resident.philsys_id_number ? (
                                        <span className="font-mono text-xs font-semibold text-slate-700 bg-slate-100 px-2.5 py-1 rounded">
                                            {resident.philsys_id_number}
                                        </span>
                                    ) : (
                                        <span className="text-xs text-slate-400 italic">Not Provided</span>
                                    )}
                                </td>
                                <td className="px-6 py-4">
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
                                        {resident.purok || 'Unassigned'}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex flex-wrap gap-1.5">
                                        {resident.philsys_id_photo && (
                                            <span className="inline-flex items-center gap-1 text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-md">
                                                <IdCard className="w-3 h-3" /> PhilSys ID
                                            </span>
                                        )}
                                        {resident.utility_billing_photo && (
                                            <span className="inline-flex items-center gap-1 text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-md">
                                                <Receipt className="w-3 h-3" /> Billing Proof
                                            </span>
                                        )}
                                        {resident.secondary_id_photo && (
                                            <span className="inline-flex items-center gap-1 text-[11px] font-medium bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-md">
                                                <FileText className="w-3 h-3" /> Secondary ID
                                            </span>
                                        )}
                                        {!resident.philsys_id_photo && !resident.utility_billing_photo && (
                                            <span className="text-xs text-slate-400 italic">No attachments</span>
                                        )}
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <button
                                            onClick={() => onInspect(resident)}
                                            className="inline-flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-sm active:scale-95"
                                            title="Inspect submitted documents"
                                        >
                                            <Eye className="w-3.5 h-3.5" />
                                            Inspect
                                        </button>
                                        <button
                                            onClick={() => onApprove(resident.id)}
                                            className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-hover text-primary-foreground px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-sm hover:shadow active:scale-95"
                                        >
                                            <CheckCircle className="w-3.5 h-3.5" />
                                            Approve
                                        </button>
                                        <button
                                            onClick={() => onReject(resident)}
                                            className="inline-flex items-center gap-1.5 bg-white border border-red-200 text-red-600 hover:bg-red-50 hover:border-red-300 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-sm active:scale-95"
                                        >
                                            <XCircle className="w-3.5 h-3.5" />
                                            Reject
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))
                    )}
                </tbody>
            </table>
        </div>
    );
};
