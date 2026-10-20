import React from 'react';
import {
    X, ShieldCheck, IdCard, Receipt, FileText, ExternalLink
} from 'lucide-react';
import { formatPurok, type Resident } from './types';
import { usePrivateMediaUrl } from '../../hooks/usePrivateMediaUrl';
import { useModalFocus } from '../../hooks/useModalFocus';

interface VerificationDossierModalProps {
    resident: Resident;
    onClose: () => void;
    onApprove: (id: number) => void;
    onReject: (resident: Resident) => void;
}

export const VerificationDossierModal: React.FC<VerificationDossierModalProps> = ({
    resident,
    onClose,
    onApprove,
    onReject,
}) => {
    const philsysMedia = usePrivateMediaUrl(resident.philsys_id_photo);
    const billingMedia = usePrivateMediaUrl(resident.utility_billing_photo);
    const secondaryIdMedia = usePrivateMediaUrl(resident.secondary_id_photo);
    const dialogRef = useModalFocus<HTMLDivElement>(true, onClose);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="verification-dossier-title"
                tabIndex={-1}
                className="bg-white rounded-2xl w-full max-w-3xl shadow-2xl border border-border flex flex-col max-h-[90vh] overflow-hidden"
            >
                {/* Modal Header */}
                <div className="p-5 border-b border-border bg-slate-50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center text-blue-700">
                            <ShieldCheck className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 id="verification-dossier-title" className="font-bold text-slate-800 text-lg">{resident.full_name}</h3>
                            <p className="text-xs text-slate-500">Applicant Dossier & Verification Proofs</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        aria-label="Close verification dossier"
                        className="p-2 hover:bg-slate-200 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Modal Body */}
                <div className="p-6 overflow-y-auto space-y-6">
                    {/* Summary Metadata Card */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-200/80 text-xs">
                        <div>
                            <span className="text-slate-400 font-medium block">Date of Birth</span>
                            <span className="font-semibold text-slate-700 mt-0.5 block">{resident.birth_date}</span>
                        </div>
                        <div>
                            <span className="text-slate-400 font-medium block">Purok</span>
                            <span className="font-semibold text-slate-700 mt-0.5 block">{formatPurok(resident.purok)}</span>
                        </div>
                        <div>
                            <span className="text-slate-400 font-medium block">Contact Number</span>
                            <span className="font-semibold text-slate-700 mt-0.5 block">{resident.contact_number || 'None'}</span>
                        </div>
                        <div>
                            <span className="text-slate-400 font-medium block">PhilSys ID Number</span>
                            <span className="font-mono font-semibold text-slate-700 mt-0.5 block">{resident.philsys_id_number || 'N/A'}</span>
                        </div>
                        <div className="col-span-2 sm:col-span-4">
                            <span className="text-slate-400 font-medium block">House / Street / Landmark</span>
                            <span className="font-semibold text-slate-700 mt-0.5 block break-words">{resident.address_details || 'Not provided'}</span>
                        </div>
                    </div>

                    {/* Uploaded Documents Grid */}
                    <div className="space-y-4">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Submitted Proof of Identity & Residency</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* 1. PhilSys ID Photo */}
                            <div className="border border-slate-200 rounded-xl p-3.5 bg-slate-50/50 flex flex-col justify-between">
                                <div>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <IdCard className="w-3.5 h-3.5 text-blue-600" />
                                            PhilSys National ID
                                        </span>
                                    </div>
                                    {resident.philsys_id_photo ? (
                                        philsysMedia.url ? (
                                            <a
                                                href={philsysMedia.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="group relative block rounded-lg overflow-hidden border border-slate-200 bg-white"
                                            >
                                                <img
                                                    src={philsysMedia.url}
                                                    alt="PhilSys ID"
                                                    className="w-full h-40 object-cover group-hover:scale-105 transition-transform"
                                                />
                                                <span className="absolute bottom-2 right-2 bg-black/70 text-white text-[10px] px-2 py-0.5 rounded flex items-center gap-1">
                                                    <ExternalLink className="w-3 h-3" /> Open
                                                </span>
                                            </a>
                                        ) : (
                                            <div role="status" className="h-40 flex items-center justify-center text-xs text-slate-500">
                                                {philsysMedia.isLoading ? "Loading protected image…" : "Unable to load protected image."}
                                            </div>
                                        )
                                    ) : (
                                        <div className="h-40 rounded-lg border-2 border-dashed border-slate-200 flex items-center justify-center text-xs text-slate-400 italic bg-white">
                                            No photo uploaded
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* 2. Utility Billing Proof */}
                            <div className="border border-slate-200 rounded-xl p-3.5 bg-slate-50/50 flex flex-col justify-between">
                                <div>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <Receipt className="w-3.5 h-3.5 text-emerald-600" />
                                            Utility Proof {resident.utility_billing_type && `(${resident.utility_billing_type})`}
                                        </span>
                                    </div>
                                    {resident.utility_billing_photo ? (
                                        billingMedia.url ? (
                                            <a
                                                href={billingMedia.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="group relative block rounded-lg overflow-hidden border border-slate-200 bg-white"
                                            >
                                                <img
                                                    src={billingMedia.url}
                                                    alt="Utility Billing"
                                                    className="w-full h-40 object-cover group-hover:scale-105 transition-transform"
                                                />
                                                <span className="absolute bottom-2 right-2 bg-black/70 text-white text-[10px] px-2 py-0.5 rounded flex items-center gap-1">
                                                    <ExternalLink className="w-3 h-3" /> Open
                                                </span>
                                            </a>
                                        ) : (
                                            <div role="status" className="h-40 flex items-center justify-center text-xs text-slate-500">
                                                {billingMedia.isLoading ? "Loading protected image…" : "Unable to load protected image."}
                                            </div>
                                        )
                                    ) : (
                                        <div className="h-40 rounded-lg border-2 border-dashed border-slate-200 flex items-center justify-center text-xs text-slate-400 italic bg-white">
                                            No bill uploaded
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* 3. Secondary ID */}
                            <div className="border border-slate-200 rounded-xl p-3.5 bg-slate-50/50 flex flex-col justify-between">
                                <div>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                                            <FileText className="w-3.5 h-3.5 text-purple-600" />
                                            Secondary ID {resident.secondary_id_type && `(${resident.secondary_id_type})`}
                                        </span>
                                    </div>
                                    {resident.secondary_id_photo ? (
                                        secondaryIdMedia.url ? (
                                            <a
                                                href={secondaryIdMedia.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="group relative block rounded-lg overflow-hidden border border-slate-200 bg-white"
                                            >
                                                <img
                                                    src={secondaryIdMedia.url}
                                                    alt="Secondary ID"
                                                    className="w-full h-40 object-cover group-hover:scale-105 transition-transform"
                                                />
                                                <span className="absolute bottom-2 right-2 bg-black/70 text-white text-[10px] px-2 py-0.5 rounded flex items-center gap-1">
                                                    <ExternalLink className="w-3 h-3" /> Open
                                                </span>
                                            </a>
                                        ) : (
                                            <div role="status" className="h-40 flex items-center justify-center text-xs text-slate-500">
                                                {secondaryIdMedia.isLoading ? "Loading protected image…" : "Unable to load protected image."}
                                            </div>
                                        )
                                    ) : (
                                        <div className="h-40 rounded-lg border-2 border-dashed border-slate-200 flex items-center justify-center text-xs text-slate-400 italic bg-white">
                                            None (Optional)
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Modal Footer Actions */}
                <div className="p-4 bg-slate-50 border-t border-border flex items-center justify-between">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg text-xs font-bold transition-colors"
                    >
                        Close Dossier
                    </button>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => onReject(resident)}
                            className="px-4 py-2 border border-red-300 text-red-600 hover:bg-red-50 rounded-lg text-xs font-bold transition-colors"
                        >
                            Reject Application
                        </button>
                        <button
                            onClick={() => onApprove(resident.id)}
                            className="px-5 py-2 bg-primary hover:bg-primary-hover text-primary-foreground rounded-lg text-xs font-bold transition-colors shadow-sm"
                        >
                            Approve Registration
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
