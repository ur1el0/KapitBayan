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

const REPORT_METRIC_OPTIONS = [
    { key: 'new_registered_residents', label: 'Newly Registered Users' },
    { key: 'rbi_transfers', label: 'RBI Transfers & Baseline' },
    { key: 'documents_issued', label: 'Documents Issued' },
    { key: 'incidents', label: 'Incidents & Issues' },
    { key: 'aid_requests', label: 'Financial Aid' },
    { key: 'equipment_borrowing', label: 'Equipment Borrowing' },
    { key: 'communications', label: 'Announcements & Activities' },
] as const;

type ReportMetricKey = (typeof REPORT_METRIC_OPTIONS)[number]['key'];
const ALL_METRIC_KEYS: ReportMetricKey[] = REPORT_METRIC_OPTIONS.map((item) => item.key);

const formatLocalDateInput = (date: Date) => {
    const offsetMs = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offsetMs).toISOString().split('T')[0];
};

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
    const firstOfMonth = new Date(currentYear, now.getMonth(), 1);
    const [periodMode, setPeriodMode] = useState<'month' | 'range'>('month');
    const [selectedYear, setSelectedYear] = useState<number>(currentYear);
    const [selectedMonth, setSelectedMonth] = useState<number>(now.getMonth() + 1);
    const [startDate, setStartDate] = useState<string>(formatLocalDateInput(firstOfMonth));
    const [endDate, setEndDate] = useState<string>(formatLocalDateInput(now));
    const [selectedMetrics, setSelectedMetrics] = useState<ReportMetricKey[]>(ALL_METRIC_KEYS);

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

    const isAllMetricsSelected = selectedMetrics.length === ALL_METRIC_KEYS.length;

    const buildFilterParams = useCallback(() => {
        const params: Record<string, string | number> =
            periodMode === 'range'
                ? { start_date: startDate, end_date: endDate }
                : { year: selectedYear, month: selectedMonth };
        if (selectedMetrics.length > 0 && selectedMetrics.length < ALL_METRIC_KEYS.length) {
            params.metrics = selectedMetrics.join(',');
        }
        return params;
    }, [periodMode, startDate, endDate, selectedYear, selectedMonth, selectedMetrics]);

    const toggleMetric = (metricKey: ReportMetricKey) => {
        setSelectedMetrics((current) => {
            if (current.includes(metricKey)) {
                if (current.length === 1) {
                    toast.error(t('Keep at least one report category selected.'));
                    return current;
                }
                return current.filter((item) => item !== metricKey);
            }
            return ALL_METRIC_KEYS.filter((item) => item === metricKey || current.includes(item));
        });
    };

    const fetchReport = useCallback(
        async (isRetry = false) => {
            if (periodMode === 'range' && (!startDate || !endDate || endDate < startDate)) {
                return;
            }
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
                        params: buildFilterParams(),
                        signal: controller.signal,
                    },
                );
                if (typeof response?.data === 'string') {
                    throw new Error('Unexpected HTML payload for accomplishment report.');
                }
                if (isAccomplishmentReport(response?.data)) {
                    setReport(response.data);
                } else {
                    setReport(createEmptyReport(selectedYear, selectedMonth));
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
        [periodMode, startDate, endDate, selectedYear, selectedMonth, buildFilterParams],
    );

    useEffect(() => {
        let cancelled = false;
        void Promise.resolve().then(() => {
            if (!cancelled) {
                void fetchReport();
            }
        });
        return () => {
            cancelled = true;
            requestControllerRef.current?.abort();
        };
    }, [fetchReport]);

    const handleExport = async (exportFormat: 'pdf' | 'csv') => {
        if (exportingFormat !== null) return;
        if (periodMode === 'range' && (!startDate || !endDate || endDate < startDate)) {
            toast.error(t('Choose a valid start and end date before exporting.'));
            return;
        }
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
                        ...buildFilterParams(),
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
            const filename =
                periodMode === 'range'
                    ? `Accomplishment_Report_${startDate}_to_${endDate}.${exportFormat}`
                    : `Accomplishment_Report_${selectedYear}_${paddedMonth}.${exportFormat}`;

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
    const activeMetricSet = new Set(
        activeReport.included_metrics && activeReport.included_metrics.length > 0
            ? activeReport.included_metrics
            : selectedMetrics,
    );
    const hasMetric = (key: ReportMetricKey) => activeMetricSet.has(key);
    const showResidentsCard = hasMetric('new_registered_residents') || hasMetric('rbi_transfers');
    const showCertificatesCard = hasMetric('documents_issued');
    const showServicesCard =
        hasMetric('incidents') || hasMetric('aid_requests') || hasMetric('equipment_borrowing');
    const showCommunicationsCard = hasMetric('communications');

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
                    <div className="inline-flex rounded-xl border border-slate-300 bg-slate-50 p-1" role="group" aria-label={t('Report Period Mode')}>
                        <button
                            type="button"
                            aria-pressed={periodMode === 'month'}
                            onClick={() => setPeriodMode('month')}
                            className={`rounded-lg px-2.5 py-1.5 text-xs font-semibold transition cursor-pointer ${periodMode === 'month' ? 'bg-primary text-primary-foreground' : 'text-slate-700 hover:bg-slate-200/70'}`}
                        >
                            {t('Monthly')}
                        </button>
                        <button
                            type="button"
                            aria-pressed={periodMode === 'range'}
                            onClick={() => setPeriodMode('range')}
                            className={`rounded-lg px-2.5 py-1.5 text-xs font-semibold transition cursor-pointer ${periodMode === 'range' ? 'bg-primary text-primary-foreground' : 'text-slate-700 hover:bg-slate-200/70'}`}
                        >
                            {t('Date Range')}
                        </button>
                    </div>

                    {periodMode === 'month' ? (
                        <>
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
                        </>
                    ) : (
                        <>
                            <label className="text-xs font-semibold text-slate-700">
                                {t('Start Date')}
                                <input
                                    type="date"
                                    aria-label={t('Start Date')}
                                    value={startDate}
                                    max={endDate}
                                    onChange={(event) => setStartDate(event.target.value)}
                                    className="mt-1 block rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-900"
                                />
                            </label>
                            <label className="text-xs font-semibold text-slate-700">
                                {t('End Date')}
                                <input
                                    type="date"
                                    aria-label={t('End Date')}
                                    value={endDate}
                                    min={startDate}
                                    onChange={(event) => setEndDate(event.target.value)}
                                    className="mt-1 block rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-900"
                                />
                            </label>
                        </>
                    )}

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

            <div className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-200/80 bg-slate-50/70 px-3.5 py-2.5">
                <span className="text-xs font-semibold text-slate-700 mr-1">
                    {t('Include in Report & Exports')}:
                </span>
                {REPORT_METRIC_OPTIONS.map((option) => {
                    const checked = selectedMetrics.includes(option.key);
                    return (
                        <button
                            key={option.key}
                            type="button"
                            aria-pressed={checked}
                            onClick={() => toggleMetric(option.key)}
                            className={`rounded-full border px-2.5 py-1 text-xs font-semibold transition cursor-pointer ${
                                checked
                                    ? 'border-primary bg-primary/10 text-primary-text'
                                    : 'border-slate-300 bg-white text-slate-500 hover:bg-slate-100'
                            }`}
                        >
                            {checked ? '✓ ' : ''}
                            {t(option.label)}
                        </button>
                    );
                })}
                {!isAllMetricsSelected && (
                    <button
                        type="button"
                        onClick={() => setSelectedMetrics(ALL_METRIC_KEYS)}
                        className="ml-auto text-xs font-semibold text-primary-text underline cursor-pointer"
                    >
                        {t('Select All')}
                    </button>
                )}
            </div>

            <div className="sr-only" role="status" aria-live="polite">
                {exportStatusMessage}
            </div>

            {loadError ? (
                <InlineErrorState
                    message={t("We couldn't load the monthly accomplishment report.")}
                    onRetry={() => void fetchReport(true)}
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
                    {showResidentsCard && (
                        <article className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                    {t('Residents & RBI Updates')}
                                </span>
                                <Users className="h-4 w-4 text-sky-700" aria-hidden="true" />
                            </div>
                            {hasMetric('new_registered_residents') && (
                                <>
                                    <p className="text-2xl font-extrabold text-slate-900">
                                        {activeReport.residents_rbi.new_registered_residents}
                                    </p>
                                    <p className="text-xs text-slate-600">
                                        {t('New registered residents')} ({activeReport.residents_rbi.new_verified_residents}{' '}
                                        {t('verified')})
                                    </p>
                                </>
                            )}
                            {hasMetric('rbi_transfers') && (
                                <div className="border-t border-slate-200/80 pt-2 text-xs text-slate-600 flex justify-between">
                                    <span>{t('Approved RBI Transfers')}:</span>
                                    <span className="font-semibold text-slate-900">
                                        {activeReport.residents_rbi.approved_rbi_transfers}
                                    </span>
                                </div>
                            )}
                        </article>
                    )}

                    {/* 2. Certificates & Document Issuance */}
                    {showCertificatesCard && (
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
                    )}

                    {/* 3. Community Issues, Aid & Equipment Services */}
                    {showServicesCard && (
                        <article className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                                    {t('Issues, Aid & Equipment')}
                                </span>
                                <ShieldCheck className="h-4 w-4 text-amber-700" aria-hidden="true" />
                            </div>
                            {hasMetric('incidents') && (
                                <>
                                    <p className="text-2xl font-extrabold text-slate-900">
                                        {activeReport.community_services.issues_resolved}
                                    </p>
                                    <p className="text-xs text-slate-600">
                                        {t('Issues resolved')} ({activeReport.community_services.issues_submitted}{' '}
                                        {t('submitted')})
                                    </p>
                                </>
                            )}
                            {(hasMetric('aid_requests') || hasMetric('equipment_borrowing')) && (
                                <div className="border-t border-slate-200/80 pt-2 text-xs text-slate-600 space-y-1">
                                    {hasMetric('aid_requests') && (
                                        <div className="flex justify-between">
                                            <span>{t('Financial Aid Approved')}:</span>
                                            <span className="font-semibold text-slate-900">
                                                {activeReport.community_services.aid_requests_approved}
                                            </span>
                                        </div>
                                    )}
                                    {hasMetric('equipment_borrowing') && (
                                        <div className="flex justify-between">
                                            <span>{t('Equipment Fulfilled')}:</span>
                                            <span className="font-semibold text-slate-900">
                                                {activeReport.community_services.equipment_requests_fulfilled}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </article>
                    )}

                    {/* 4. Public Communications & Activities */}
                    {showCommunicationsCard && (
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
                    )}
                </div>
            )}
        </section>
    );
};
