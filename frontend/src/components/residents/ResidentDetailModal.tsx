import React from 'react';
import {
    X, CheckCircle2, User, Phone, ShieldCheck,
    ExternalLink, FileText, Home
} from 'lucide-react';
import type { Resident } from './types';
import { usePrivateMediaUrl } from '../../hooks/usePrivateMediaUrl';
import { useModalFocus } from '../../hooks/useModalFocus';

interface ResidentDetailModalProps {
    resident: Resident;
    emailDraft: string;
    setEmailDraft: (value: string) => void;
    savingEmail: boolean;
    onSaveEmail: () => void;
    onClose: () => void;
    getAge: (birthDateStr: string) => string;
}

export const ResidentDetailModal: React.FC<ResidentDetailModalProps> = ({
    resident,
    emailDraft,
    setEmailDraft,
    savingEmail,
    onSaveEmail,
    onClose,
    getAge,
}) => {
    const philsysMedia = usePrivateMediaUrl(resident.philsys_id_photo);
    const secondaryIdMedia = usePrivateMediaUrl(resident.secondary_id_photo);
    const billingMedia = usePrivateMediaUrl(resident.utility_billing_photo);
    const dialogRef = useModalFocus<HTMLDivElement>(true, onClose);

    const isEmailUnchanged = emailDraft.trim().toLowerCase() === (resident.email ?? '').trim().toLowerCase();

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="resident-detail-title"
                tabIndex={-1}
                className="bg-white rounded-3xl shadow-2xl max-w-2xl w-full overflow-hidden border border-slate-100 flex flex-col max-h-[90vh]"
            >
                {/* Modal Header */}
                <div className="px-6 py-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/80">
                    <div className="flex items-center gap-3.5">
                        <div className="w-12 h-12 rounded-2xl bg-primary text-primary-foreground flex items-center justify-center font-bold text-lg shadow-sm">
                            {resident.full_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <h3 id="resident-detail-title" className="text-lg font-bold text-slate-900">{resident.full_name}</h3>
                            <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500">
                                <span className="font-mono">Account ID: @{resident.username || 'resident'}</span>
                                <span>•</span>
                                <span className="inline-flex items-center gap-1 font-semibold text-emerald-600">
                                    <CheckCircle2 className="w-3.5 h-3.5" /> Verified Citizen
                                </span>
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        aria-label="Close resident dossier"
                        className="text-slate-400 hover:text-slate-600 p-1.5 rounded-xl hover:bg-slate-200 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Modal Body */}
                <div className="p-6 overflow-y-auto space-y-6">
                    {/* Personal & Contact Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-3">
                            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                                <User className="w-3.5 h-3.5 text-primary-text" /> Personal Demographics
                            </div>
                            <div className="space-y-1.5 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-slate-500">Birth Date:</span>
                                    <span className="font-semibold text-slate-800">{resident.birth_date}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-500">Age:</span>
                                    <span className="font-semibold text-slate-800">{getAge(resident.birth_date)}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-500">Purok / Zone:</span>
                                    <span className="font-semibold text-slate-800">{resident.purok || 'Not Specified'}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500">House / Street / Landmark:</span>
                                    <span className="font-semibold text-slate-800 block break-words">{resident.address_details || 'Not provided'}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-500">Voter Status:</span>
                                    <span className={`font-semibold ${resident.voter_status ? 'text-emerald-600' : 'text-slate-500'}`}>
                                        {resident.voter_status ? 'Registered Voter' : 'Non-Voter'}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-3">
                            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                                <Phone className="w-3.5 h-3.5 text-primary-text" /> Contact Information
                            </div>
                            <div className="space-y-1.5 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-slate-500">Contact Number:</span>
                                    <span className="font-semibold text-slate-800">{resident.contact_number || 'N/A'}</span>
                                </div>
                                <div className="space-y-1.5">
                                    <label
                                        htmlFor="resident-login-email"
                                        className="block text-slate-500"
                                    >
                                        Login Email
                                    </label>
                                    <input
                                        id="resident-login-email"
                                        type="email"
                                        autoComplete="email"
                                        required
                                        value={emailDraft}
                                        onChange={(event) => setEmailDraft(event.target.value)}
                                        disabled={savingEmail}
                                        aria-describedby="resident-login-email-help"
                                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-60"
                                    />
                                    <p
                                        id="resident-login-email-help"
                                        className="text-xs text-slate-500"
                                    >
                                        Enter an address the resident confirms in person.
                                        They must control this inbox to complete password reset.
                                    </p>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-500">System Role:</span>
                                    <span className="font-semibold text-primary-text">Resident</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Official Identification & PhilSys Proof */}
                    <div className="p-5 rounded-2xl border border-primary/20 bg-primary/5 space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="text-xs font-bold text-primary-text uppercase tracking-wider flex items-center gap-1.5">
                                <ShieldCheck className="w-4 h-4 text-primary-text" /> Philippine National ID (PhilSys)
                            </div>
                            {resident.philsys_id_number ? (
                                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-primary/10 text-primary-text">
                                    Verified Card
                                </span>
                            ) : (
                                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-500">
                                    No PhilSys on Record
                                </span>
                            )}
                        </div>

                        <div className="bg-white p-3.5 rounded-xl border border-blue-100 flex items-center justify-between">
                            <div>
                                <div className="text-[11px] text-slate-500">PhilSys Card Number</div>
                                <div className="font-mono font-bold text-slate-900 text-sm">
                                    {resident.philsys_id_number || 'Not registered via PhilSys'}
                                </div>
                            </div>
                            {resident.philsys_id_photo && (
                                philsysMedia.url ? (
                                    <a
                                        href={philsysMedia.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1 text-xs font-bold text-primary-text hover:underline"
                                    >
                                        <span>View ID Photo</span>
                                        <ExternalLink className="w-3.5 h-3.5" />
                                    </a>
                                ) : (
                                    <span role="status" className="text-xs text-slate-500">
                                        {philsysMedia.isLoading ? "Loading attachment…" : "Unable to load attachment."}
                                    </span>
                                )
                            )}
                        </div>
                    </div>

                    {/* Secondary Valid ID & Utility Billing Proofs */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-2">
                            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                                <FileText className="w-3.5 h-3.5 text-slate-500" /> Secondary Valid ID
                            </div>
                            <div className="text-sm">
                                <span className="text-slate-500">Type: </span>
                                <span className="font-semibold text-slate-800">{resident.secondary_id_type || 'None provided'}</span>
                            </div>
                            {resident.secondary_id_photo ? (
                                secondaryIdMedia.url ? (
                                    <a
                                        href={secondaryIdMedia.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1 text-xs font-bold text-primary-text hover:underline mt-1"
                                    >
                                        <span>View Attached ID Photo</span>
                                        <ExternalLink className="w-3 h-3" />
                                    </a>
                                ) : (
                                    <span role="status" className="text-xs text-slate-500">
                                        {secondaryIdMedia.isLoading ? "Loading attachment…" : "Unable to load attachment."}
                                    </span>
                                )
                            ) : (
                                <div className="text-xs text-slate-400 italic">No secondary photo uploaded.</div>
                            )}
                        </div>

                        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-2">
                            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                                <Home className="w-3.5 h-3.5 text-slate-500" /> Proof of Residency
                            </div>
                            <div className="text-sm">
                                <span className="text-slate-500">Type: </span>
                                <span className="font-semibold text-slate-800">{resident.utility_billing_type || 'Utility / House Billing'}</span>
                            </div>
                            {resident.utility_billing_photo ? (
                                billingMedia.url ? (
                                    <a
                                        href={billingMedia.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1 text-xs font-bold text-primary-text hover:underline mt-1"
                                    >
                                        <span>View Billing Receipt</span>
                                        <ExternalLink className="w-3 h-3" />
                                    </a>
                                ) : (
                                    <span role="status" className="text-xs text-slate-500">
                                        {billingMedia.isLoading ? "Loading attachment…" : "Unable to load attachment."}
                                    </span>
                                )
                            ) : (
                                <div className="text-xs text-slate-400 italic">No utility billing attached.</div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row sm:justify-between gap-3">
                    <button
                        type="button"
                        onClick={onClose}
                        className="w-full sm:w-auto px-5 py-2 rounded-xl text-sm font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer shadow-2xs"
                    >
                        Close Dossier
                    </button>
                    <button
                        type="button"
                        onClick={onSaveEmail}
                        disabled={savingEmail || !emailDraft.trim() || isEmailUnchanged}
                        className="w-full sm:w-auto px-5 py-2 rounded-xl text-sm font-semibold bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {savingEmail ? "Saving..." : "Save Login Email"}
                    </button>
                </div>
            </div>
        </div>
    );
};
