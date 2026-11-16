import React, { useCallback, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import {
    Calendar,
    Download,
    FileSpreadsheet,
    FileText,
    Loader2,
    Megaphone,
    ShieldCheck,
    Users,
} from 'lucide-react';
import { axiosPrivate } from '../../api/axios';
import { InlineErrorState } from '../ui/InlineErrorState';
import { useLanguage } from '../../context/language-context';
import type { AccomplishmentReport } from './types';

const MONTHS = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' },
];

const isRecord = (value: unknown): value is Record<string, unknown> =>
    typeof value === 'object' && value !== null && !Array.isArray(value);

const isAccomplishmentReport = (value: unknown): value is AccomplishmentReport =>
    isRecord(value)
    && typeof value.barangay_name === 'string'
    && typeof value.period_label === 'string'
    && isRecord(value.residents_rbi)
    && isRecord(value.certificates_issuance)
    && isRecord(value.community_services)
    && isRecord(value.communications_activities);

const createEmptyReport = (year: number, month: number): AccomplishmentReport => {
    const monthLabel = MONTHS.find((item) => item.value === month)?.label ?? 'Month';
    return {
        barangay_name: '',
        municipality: '',
        province: '',
        captain_name: '',
        year,
        month,
        period_label: `${monthLabel} ${year}`,
        generated_at: '',
        residents_rbi: {
            new_registered_residents: 0,
            new_verified_residents: 0,
            approved_rbi_transfers: 0,
            total_active_verified_residents: 0,
        },
        certificates_issuance: {
            total_requests: 0,
            total_issued: 0,
            fee_waived_or_exempt_count: 0,
            by_document_type: [],
        },
        community_services: {
            issues_submitted: 0,
            issues_resolved: 0,
            aid_requests_submitted: 0,
            aid_requests_approved: 0,
            equipment_requests_fulfilled: 0,
            equipment_requests_returned: 0,
        },
        communications_activities: {
            announcements_published: 0,
            activities_conducted: 0,
        },
    };
};

export const AccomplishmentReportCard: React.FC = () => {
    const { t } = useLanguage();
    const now = new Date();
    const currentYear = now.getFullYear();
    const [selectedYear, setSelectedYear] = useState<number>(currentYear);
    const [selectedMonth, setSelectedMonth] = useState<number>(now.getMonth() + 1);

    const [report, setReport] = useState<AccomplishmentReport | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [loadError, setLoadError] = useState<boolean>(false);
    const [retrying, setRetrying] = useState<boolean>(false);
    const [exportingFormat, setExportingFormat] = useState<'pdf' | 'csv' | null>(null);
    const [exportStatusMessage, setExportStatusMessage] = useState<string>('');
    const requestControllerRef = useRef<AbortController | null>(null);

    const yearOptions = [
        currentYear - 2,
        currentYear - 1,
        currentYear,
        currentYear + 1,
    ];

    const fetchReport = useCallback(
        async (year: number, month: number, isRetry = false) => {
            requestControllerRef.current?.abort();
            const controller = new AbortController();
            requestControllerRef.current = controller;

            if (isRetry) {
                setRetrying(true);
            } else {
                setLoading(true);
            }

            try {
                const response = await axiosPrivate.get(
                    '/dashboard/accomplishment-report/',
                    {
                        params: { year, month },
                        signal: controller.signal,
                    },
                );
                if (typeof response?.data === 'string') {
                    throw new Error('Unexpected HTML payload for accomplishment report.');
                }
                if (isAccomplishmentReport(response?.data)) {
                    setReport(response.data);
                } else {
                    setReport(createEmptyReport(year, month));
                }
                setLoadError(false);
            } catch {
                if (!controller.signal.aborted) {
                    setLoadError(true);
                }
            } finally {
                if (requestControllerRef.current === controller) {
                    requestControllerRef.current = null;
                    setLoading(false);
                    setRetrying(false);
                }
            }
        },
        [],
    );

    useEffect(() => {
        let cancelled = false;
        void Promise.resolve().then(() => {
            if (!cancelled) {
                void fetchReport(selectedYear, selectedMonth);
            }
        });
        return () => {
            cancelled = true;
            requestControllerRef.current?.abort();
        };
    }, [selectedYear, selectedMonth, fetchReport]);

    const handleExport = async (exportFormat: 'pdf' | 'csv') => {
        if (exportingFormat !== null) return;
        setExportingFormat(exportFormat);
        setExportStatusMessage(
            t(
                exportFormat === 'pdf'
                    ? 'Generating PDF accomplishment report…'
                    : 'Generating CSV accomplishment report…',
            ),
        );

        try {
            const response = await axiosPrivate.get(
                '/dashboard/accomplishment-report/export/',
                {
                    params: {
                        year: selectedYear,
                        month: selectedMonth,
                        export_format: exportFormat,
                    },
                    responseType: 'blob',
                },
            );

            const contentType =
                exportFormat === 'pdf'
                    ? 'application/pdf'
                    : 'text/csv;charset=utf-8;';
            const blob =
                response.data instanceof Blob
                    ? response.data
                    : new Blob([response.data ?? ''], { type: contentType });

            const paddedMonth = String(selectedMonth).padStart(2, '0');
            const filename = `Accomplishment_Report_${selectedYear}_${paddedMonth}.${exportFormat}`;

            if (typeof URL.createObjectURL === 'function') {
                const url = URL.createObjectURL(blob);
                const anchor = document.createElement('a');
                anchor.href = url;
                anchor.download = filename;
                document.body.appendChild(anchor);
                anchor.click();
                anchor.remove();
                if (typeof URL.revokeObjectURL === 'function') {
                    URL.revokeObjectURL(url);
                }
            }

            const doneMsg = t(
                exportFormat === 'pdf'
                    ? 'Accomplishment report PDF downloaded.'
                    : 'Accomplishment report CSV downloaded.',
            );
            setExportStatusMessage(doneMsg);
            toast.success(doneMsg);
        } catch {
            const errMsg = t('Could not export accomplishment report. Please try again.');
            setExportStatusMessage(errMsg);
            toast.error(errMsg);
        } finally {
            setExportingFormat(null);
        }
    };

    const activeReport = report ?? createEmptyReport(selectedYear, selectedMonth);

    return (
        <section
            aria-labelledby="accomplishment-report-heading"
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-5"
        >
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 border-b border-slate-100 pb-4">
                <div>
                    <div className="flex items-center gap-2">
                        <FileText className="h-5 w-5 text-primary-text" aria-hidden="true" />
                        <h2
                            id="accomplishment-report-heading"
                            className="text-lg font-extrabold text-slate-900"
                        >
                            {t('Monthly Barangay Accomplishment Report')}
                        </h2>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">
                        {t(
                            'Executive summary of monthly resident updates, clearances issued, community services, and activities for official reporting.',
                        )}
                    </p>
                </div>

                <div className="flex flex-wrap items-end gap-3">
                    <label className="text-xs font-semibold text-slate-700">
                        {t('Report Month')}
                        <select
                            aria-label={t('Report Month')}
                            value={selectedMonth}
                            onChange={(event) => setSelectedMonth(Number(event.target.value))}
                            className="mt-1 block rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-900"
                        >
                            {MONTHS.map((m) => (
                                <option key={m.value} value={m.value}>
                                    {t(m.label)}
                                </option>
                            ))}
                        </select>
                    </label>

                    <label className="text-xs font-semibold text-slate-700">
                        {t('Report Year')}
                        <select
                            aria-label={t('Report Year')}
                            value={selectedYear}
                            onChange={(event) => setSelectedYear(Number(event.target.value))}
                            className="mt-1 block rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-900"
                        >
                            {yearOptions.map((yr) => (
                                <option key={yr} value={yr}>
                                    {yr}
                                </option>
                            ))}
                        </select>
                    </label>

                    <div className="flex items-center gap-2">
                        <button
                            type="button"
                            disabled={exportingFormat !== null}
                            onClick={() => void handleExport('pdf')}
                            className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground shadow-xs transition hover:opacity-95 disabled:opacity-60 cursor-pointer"
                        >
                            {exportingFormat === 'pdf' ? (
                                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                            ) : (
                                <Download className="h-4 w-4" aria-hidden="true" />
                            )}
                            <span>{t('Export PDF')}</span>
                        </button>

                        <button
                            type="button"
                            disabled={exportingFormat !== null}
                            onClick={() => void handleExport('csv')}
                            className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 transition hover:bg-slate-50 disabled:opacity-60 cursor-pointer"
                        >
                            {exportingFormat === 'csv' ? (
                                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                            ) : (
                                <FileSpreadsheet className="h-4 w-4" aria-hidden="true" />
                            )}
                            <span>{t('Export CSV')}</span>
                        </button>
                    </div>
                </div>
            </div>

            <div className="sr-only" role="status" aria-live="polite">
                {exportStatusMessage}
            </div>

            {loadError ? (
                <InlineErrorState
                    message={t("We couldn't load the monthly accomplishment report.")}
                    onRetry={() => void fetchReport(selectedYear, selectedMonth, true)}
                    retrying={retrying}
                />
            ) : loading ? (
                <div
                    aria-label={t('Loading accomplishment report…')}
                    className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
                >
                    {[1, 2, 3, 4].map((index) => (
                        <div
                            key={index}
                            className="h-36 animate-pulse rounded-xl border border-slate-100 bg-slate-50 p-4"
                        />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    {/* 1. Residents & RBI Updates */}
                    <article className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                {t('Residents & RBI Updates')}
                            </span>
                            <Users className="h-4 w-4 text-sky-700" aria-hidden="true" />
                        </div>
                        <p className="text-2xl font-extrabold text-slate-900">
                            {activeReport.residents_rbi.new_registered_residents}
                        </p>
                        <p className="text-xs text-slate-600">
                            {t('New registered residents')} ({activeReport.residents_rbi.new_verified_residents}{' '}
                            {t('verified')})
                        </p>
                        <div className="border-t border-slate-200/80 pt-2 text-xs text-slate-600 flex justify-between">
                            <span>{t('Approved RBI Transfers')}:</span>
                            <span className="font-semibold text-slate-900">
                                {activeReport.residents_rbi.approved_rbi_transfers}
                            </span>
                        </div>
                    </article>

                    {/* 2. Certificates & Document Issuance */}
                    <article className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                {t('Certificates Issued')}
                            </span>
                            <FileText className="h-4 w-4 text-emerald-700" aria-hidden="true" />
                        </div>
                        <p className="text-2xl font-extrabold text-slate-900">
                            {activeReport.certificates_issuance.total_issued}
                        </p>
                        <p className="text-xs text-slate-600">
                            {t('Fee-waived / FTJ exempt')}:{' '}
                            <span className="font-semibold text-slate-900">
                                {activeReport.certificates_issuance.fee_waived_or_exempt_count}
                            </span>
                        </p>
                        <div className="border-t border-slate-200/80 pt-2 text-xs text-slate-600 space-y-1">
                            {activeReport.certificates_issuance.by_document_type.length === 0 ? (
                                <span>{t('No certificates released this month.')}</span>
                            ) : (
                                activeReport.certificates_issuance.by_document_type
                                    .slice(0, 2)
                                    .map((item) => (
                                        <div
                                            key={item.document_type}
                                            className="flex items-center justify-between gap-2"
                                        >
                                            <span className="truncate">{t(item.document_type)}</span>
                                            <span className="font-semibold text-slate-900">
                                                {item.count}
                                            </span>
                                        </div>
                                    ))
                            )}
                        </div>
                    </article>

                    {/* 3. Community Issues, Aid & Equipment Services */}
                    <article className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                {t('Issues, Aid & Equipment')}
                            </span>
                            <ShieldCheck className="h-4 w-4 text-amber-700" aria-hidden="true" />
                        </div>
                        <p className="text-2xl font-extrabold text-slate-900">
                            {activeReport.community_services.issues_resolved}
                        </p>
                        <p className="text-xs text-slate-600">
                            {t('Issues resolved')} ({activeReport.community_services.issues_submitted}{' '}
                            {t('submitted')})
                        </p>
                        <div className="border-t border-slate-200/80 pt-2 text-xs text-slate-600 flex justify-between">
                            <span>{t('Aid & Equipment Fulfilled')}:</span>
                            <span className="font-semibold text-slate-900">
                                {activeReport.community_services.aid_requests_approved +
                                    activeReport.community_services.equipment_requests_fulfilled}
                            </span>
                        </div>
                    </article>

                    {/* 4. Public Communications & Activities */}
                    <article className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                {t('Communications & Events')}
                            </span>
                            <Megaphone className="h-4 w-4 text-indigo-700" aria-hidden="true" />
                        </div>
                        <p className="text-2xl font-extrabold text-slate-900">
                            {activeReport.communications_activities.announcements_published}
                        </p>
                        <p className="text-xs text-slate-600">
                            {t('Public announcements published')}
                        </p>
                        <div className="border-t border-slate-200/80 pt-2 text-xs text-slate-600 flex items-center justify-between">
                            <span className="inline-flex items-center gap-1">
                                <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
                                {t('Activities conducted')}:
                            </span>
                            <span className="font-semibold text-slate-900">
                                {activeReport.communications_activities.activities_conducted}
                            </span>
                        </div>
                    </article>
                </div>
            )}
        </section>
    );
};
