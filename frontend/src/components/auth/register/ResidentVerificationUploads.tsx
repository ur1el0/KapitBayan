import React from 'react';
import { IdCard, ChevronDown } from 'lucide-react';
import { TextField } from '../../ui/TextField';
import { FileUploadZone } from '../../ui/FileUploadZone';
import { useLanguage } from '../../../context/language-context';

interface ResidentVerificationUploadsProps {
    isExpanded: boolean;
    onToggleExpand: () => void;
    philsysIdNumber: string;
    onPhilsysIdNumberChange: (val: string) => void;
    philsysPhoto: File | null;
    onPhilsysPhotoChange: (file: File | null) => void;
    utilityBillingType: string;
    onUtilityBillingTypeChange: (val: string) => void;
    utilityBillingPhoto: File | null;
    onUtilityBillingPhotoChange: (file: File | null) => void;
    secondaryIdType: string;
    onSecondaryIdTypeChange: (val: string) => void;
    secondaryIdPhoto: File | null;
    onSecondaryIdPhotoChange: (file: File | null) => void;
}

export const ResidentVerificationUploads: React.FC<ResidentVerificationUploadsProps> = ({
    isExpanded,
    onToggleExpand,
    philsysIdNumber,
    onPhilsysIdNumberChange,
    philsysPhoto,
    onPhilsysPhotoChange,
    utilityBillingType,
    onUtilityBillingTypeChange,
    utilityBillingPhoto,
    onUtilityBillingPhotoChange,
    secondaryIdType,
    onSecondaryIdTypeChange,
    secondaryIdPhoto,
    onSecondaryIdPhotoChange,
}) => {
    const { t } = useLanguage();
    const utilityBillingTypeId = React.useId();
    const secondaryIdTypeId = React.useId();
    const hasUploadedProof = Boolean(philsysPhoto || utilityBillingPhoto || secondaryIdPhoto);

    return (
        <div className="border border-slate-200 rounded-xl bg-slate-50/70 overflow-hidden transition-all shadow-sm">
            <button
                type="button"
                aria-expanded={isExpanded}
                onClick={onToggleExpand}
                className="w-full flex items-center justify-between p-3.5 cursor-pointer text-left hover:bg-slate-100/70 transition-colors select-none"
            >
                <div className="flex items-center gap-2.5">
                    <IdCard className="w-4 h-4 text-[#0284C7] shrink-0" />
                    <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                            {t('Identity & Residency Verification')}
                        </h4>
                        <p className="text-[11px] text-slate-500">
                            {isExpanded
                                ? t('Tap to collapse verification documents')
                                : hasUploadedProof
                                    ? t('Verification document attached')
                                    : t('Required: upload at least one ID or proof of residency')}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    {hasUploadedProof && (
                        <span className="text-[10px] bg-emerald-100 text-emerald-700 font-bold px-2 py-0.5 rounded-full">
                            {t('Document Attached')}
                        </span>
                    )}
                    <ChevronDown className={"w-4 h-4 text-slate-400 transition-transform duration-200 " + (isExpanded ? "rotate-180" : "")} />
                </div>
            </button>

            {isExpanded && (
                <div className="p-3.5 pt-3 space-y-4 border-t border-slate-200 bg-white">
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                        {t('Upload at least one image to register: a PhilSys ID, a secondary valid ID, or proof of residency such as a utility bill or lease. A typed ID number alone does not count.')}
                    </p>

                    {/* 1. PhilSys ID Number & Photo */}
                    <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-3">
                        <TextField
                            label={t('PHILSYS NATIONAL ID NUMBER')}
                            type="text"
                            value={philsysIdNumber}
                            onChange={(e) => onPhilsysIdNumberChange(e.target.value)}
                            placeholder="e.g. 1234-5678-9012-3456"
                            className="font-mono"
                        />
                        <FileUploadZone
                            label={t('UPLOAD PHILSYS ID CARD PHOTO')}
                            file={philsysPhoto}
                            onFileChange={onPhilsysPhotoChange}
                        />
                    </div>

                    {/* 2. Utility Billing Residency Proof */}
                    <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-3">
                        <div>
                            <label htmlFor={utilityBillingTypeId} className="block text-[10px] font-bold tracking-wider text-slate-600 uppercase mb-1">
                                {t('SELECT PRIMARY RESIDENCY PROOF')}
                            </label>
                            <select
                                id={utilityBillingTypeId}
                                value={utilityBillingType}
                                onChange={(e) => onUtilityBillingTypeChange(e.target.value)}
                                className="w-full px-3 py-2 bg-white border border-slate-200 focus:border-[#0284C7] rounded-lg text-xs font-semibold text-slate-700 outline-none transition-all cursor-pointer"
                            >
                                <option value="Electric Bill">{t('Electric Bill')} (Meralco/Quezelco)</option>
                                <option value="Water Bill">{t('Water Bill')} (PrimeWater/Maynilad)</option>
                                <option value="Internet / Telco Bill">{t('Internet / Telco Bill')}</option>
                                <option value="Lease Agreement">{t('Residential Lease Contract')}</option>
                            </select>
                        </div>
                        <FileUploadZone
                            label={t('UPLOAD RECENT UTILITY BILL (LAST 3 MONTHS)')}
                            file={utilityBillingPhoto}
                            onFileChange={onUtilityBillingPhotoChange}
                        />
                    </div>

                    {/* 3. Secondary ID Proof */}
                    <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-3">
                        <div>
                            <label htmlFor={secondaryIdTypeId} className="block text-[10px] font-bold tracking-wider text-slate-600 uppercase mb-1 flex items-center gap-2">
                                {t('SECONDARY ID')} <span className="text-[9px] font-bold text-slate-400 bg-slate-200 px-1.5 py-0.5 rounded uppercase">{t('Optional')}</span>
                            </label>
                            <select
                                id={secondaryIdTypeId}
                                value={secondaryIdType}
                                onChange={(e) => onSecondaryIdTypeChange(e.target.value)}
                                className="w-full px-3 py-2 bg-white border border-slate-200 focus:border-[#0284C7] rounded-lg text-xs font-semibold text-slate-700 outline-none transition-all cursor-pointer"
                            >
                                <option value="">{t('None (I only have PhilSys ID)')}</option>
                                <option value="Voter ID">Voter's ID / Certification</option>
                                <option value="Driver License">Driver's License</option>
                                <option value="Passport">Passport</option>
                                <option value="Senior Citizen ID">Senior Citizen ID</option>
                                <option value="Student ID">Student ID (If Minor)</option>
                            </select>
                        </div>
                        <FileUploadZone
                            label={t('UPLOAD SECONDARY ID PHOTO')}
                            file={secondaryIdPhoto}
                            onFileChange={onSecondaryIdPhotoChange}
                            disabled={!secondaryIdType}
                        />
                    </div>
                </div>
            )}
        </div>
    );
};
