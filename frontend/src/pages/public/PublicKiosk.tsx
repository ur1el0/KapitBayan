import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { AlertTriangle, FileText, Loader2, ShieldCheck, TicketCheck, UsersRound } from 'lucide-react';
import { LanguageSwitcher } from '../../components/language/LanguageSwitcher';
import { useLanguage } from '../../context/language-context';
import { resolveApiBaseUrl } from '../../api/axios';

type Service = 'queue' | 'documents' | 'reports';
type PublicBarangay = { id: number; name: string; municipality: string; province: string };
type SubmissionResult = { reference: string; status: string; service: Service };

const INITIAL_FORM = {
    walkin_name: '',
    walkin_purok: '',
    service_type: 'Document Processing & Clearances',
    document_type: 'Barangay Clearance',
    purpose: '',
    category: 'OTHER',
    title: '',
    description: '',
    location: '',
    privacy_acknowledged: false,
};

const CATEGORY_OPTIONS = [
    ['PEACE_AND_ORDER', 'Peace and order'],
    ['PUBLIC_HEALTH', 'Public health'],
    ['INFRASTRUCTURE', 'Infrastructure'],
    ['ENVIRONMENT', 'Environment'],
    ['OTHER', 'Other'],
] as const;

const DOCUMENT_OPTIONS = [
    'Barangay Clearance',
    'Certificate of Indigency',
    'Certificate of Residency',
    'Barangay Business Clearance',
] as const;

const QUEUE_OPTIONS = [
    'Document Processing & Clearances',
    'Barangay ID Application',
    'Certificate of Indigency',
    'General Inquiries & Complaints',
] as const;

export function PublicKiosk() {
    const { t } = useLanguage();
    const [barangays, setBarangays] = useState<PublicBarangay[]>([]);
    const [barangayId, setBarangayId] = useState('');
    const [directoryLoading, setDirectoryLoading] = useState(true);
    const [directoryError, setDirectoryError] = useState(false);
    const [service, setService] = useState<Service>('queue');
    const [form, setForm] = useState(INITIAL_FORM);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [result, setResult] = useState<SubmissionResult | null>(null);

    const registrationUrl = useMemo(() => `${window.location.origin}/register`, []);

    const loadBarangays = useCallback(async () => {
        setDirectoryLoading(true);
        setDirectoryError(false);
        try {
            const response = await fetch(`${resolveApiBaseUrl()}/auth/public/barangays/`, {
                method: 'GET',
                credentials: 'omit',
                headers: { Accept: 'application/json' },
            });
            if (!response.ok) throw new Error('directory unavailable');
            const payload = await response.json();
            if (!Array.isArray(payload)) throw new Error('invalid directory');
            setBarangays(payload);
            setBarangayId((current) => current || (payload.length === 1 ? String(payload[0].id) : ''));
        } catch {
            setDirectoryError(true);
        } finally {
            setDirectoryLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadBarangays();
    }, [loadBarangays]);

    const resetKiosk = useCallback(() => {
        setService('queue');
        setForm(INITIAL_FORM);
        setError('');
        setResult(null);
    }, []);

    useEffect(() => {
        let timeout = 0;
        const scheduleReset = () => {
            window.clearTimeout(timeout);
            timeout = window.setTimeout(resetKiosk, 120_000);
        };
        scheduleReset();
        document.addEventListener('pointerdown', scheduleReset);
        document.addEventListener('keydown', scheduleReset);
        document.addEventListener('touchstart', scheduleReset);
        return () => {
            window.clearTimeout(timeout);
            document.removeEventListener('pointerdown', scheduleReset);
            document.removeEventListener('keydown', scheduleReset);
            document.removeEventListener('touchstart', scheduleReset);
        };
    }, [resetKiosk]);

    const setValue = (key: keyof typeof INITIAL_FORM, value: string | boolean) => {
        setForm((current) => ({ ...current, [key]: value }));
    };

    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setSubmitting(true);
        setError('');
        const path: Record<Service, string> = {
            queue: 'queue',
            documents: 'documents',
            reports: 'reports',
        };
        const common = {
            barangay_id: Number(barangayId),
            privacy_acknowledged: form.privacy_acknowledged,
        };
        let payload: Record<string, unknown> = common;
        if (service === 'queue') {
            payload = { ...common, walkin_name: form.walkin_name, service_type: form.service_type };
        } else if (service === 'documents') {
            payload = {
                ...common,
                walkin_name: form.walkin_name,
                walkin_purok: form.walkin_purok,
                document_type: form.document_type,
                purpose: form.purpose,
            };
        } else {
            payload = {
                ...common,
                walkin_name: form.walkin_name,
                category: form.category,
                title: form.title,
                description: form.description,
                location: form.location,
            };
        }

        try {
            const response = await fetch(`${resolveApiBaseUrl()}/kiosk/${path[service]}/`, {
                method: 'POST',
                credentials: 'omit',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify(payload),
            });
            const body = await response.json().catch(() => ({}));
            if (!response.ok || typeof body.reference !== 'string') {
                throw new Error('submission failed');
            }
            setResult({ reference: body.reference, status: body.status, service });
            setForm(INITIAL_FORM);
        } catch {
            setError(t('We could not submit this request. Check the information and try again, or ask barangay staff for help.'));
        } finally {
            setSubmitting(false);
        }
    };

    const selectedBarangay = barangays.find((barangay) => String(barangay.id) === barangayId);

    const serviceTabs: { id: Service; label: string; icon: React.ReactNode }[] = [
        { id: 'queue', label: t('Get a Queue Ticket'), icon: <TicketCheck aria-hidden="true" /> },
        { id: 'documents', label: t('Request a Document'), icon: <FileText aria-hidden="true" /> },
        { id: 'reports', label: t('Report an Issue'), icon: <AlertTriangle aria-hidden="true" /> },
    ];

    return (
        <main className="min-h-screen bg-slate-50 text-slate-900">
            <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
                <div>
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">KapitBayan</p>
                    <h1 className="mt-1 text-xl font-extrabold">{t('Barangay Public Service Kiosk')}</h1>
                </div>
                <div className="flex items-center gap-3">
                    <LanguageSwitcher compact />
                    <span className="hidden items-center gap-2 rounded-full bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800 sm:inline-flex">
                        <ShieldCheck className="h-4 w-4" aria-hidden="true" /> {t('Public walk-in mode')}
                    </span>
                </div>
            </header>

            <div className="mx-auto grid max-w-6xl gap-6 px-4 py-6 sm:px-8 lg:grid-cols-[minmax(0,1fr)_280px] lg:py-10">
                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
                    <div className="mb-6">
                        <h2 className="text-2xl font-extrabold">{t('How can we help you today?')}</h2>
                        <p className="mt-2 text-sm leading-6 text-slate-600">{t('Choose a service to make a walk-in request without signing in.')}</p>
                    </div>

                    <label className="mb-6 block text-sm font-semibold text-slate-800">
                        {t('Barangay')}
                        <select
                            required
                            value={barangayId}
                            disabled={directoryLoading || barangays.length === 0}
                            onChange={(event) => setBarangayId(event.target.value)}
                            className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm"
                        >
                            <option value="">{directoryLoading ? t('Loading…') : t('Select your Barangay')}</option>
                            {barangays.map((barangay) => (
                                <option key={barangay.id} value={barangay.id}>
                                    {barangay.name} ({barangay.municipality}, {barangay.province})
                                </option>
                            ))}
                        </select>
                    </label>

                    {directoryError && (
                        <div role="alert" className="mb-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
                            <p>{t('Barangay list could not be loaded.')}</p>
                            <button type="button" onClick={() => void loadBarangays()} className="mt-2 min-h-10 font-bold underline">
                                {t('Try again')}
                            </button>
                        </div>
                    )}
                    {!directoryLoading && !directoryError && barangays.length === 0 && (
                        <p role="status" className="mb-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">
                            {t('No approved Barangays are available for kiosk service yet.')}
                        </p>
                    )}

                    {!result && (
                        <>
                            <div className="mb-6 grid gap-2 sm:grid-cols-3" role="tablist" aria-label={t('Choose a service')}>
                                {serviceTabs.map((tab) => (
                                    <button
                                        key={tab.id}
                                        type="button"
                                        role="tab"
                                        aria-selected={service === tab.id}
                                        onClick={() => { setService(tab.id); setError(''); }}
                                        className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border px-3 text-sm font-bold ${service === tab.id ? 'border-primary bg-primary text-white' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
                                    >
                                        {tab.icon}{tab.label}
                                    </button>
                                ))}
                            </div>

                            <form onSubmit={handleSubmit} className="space-y-4">
                                {service !== 'reports' && (
                                    <TextField
                                        label={t('Full name')}
                                        value={form.walkin_name}
                                        onChange={(value) => setValue('walkin_name', value)}
                                        required
                                        maxLength={255}
                                    />
                                )}
                                {service === 'queue' && (
                                    <SelectField
                                        label={t('Service')}
                                        value={form.service_type}
                                        onChange={(value) => setValue('service_type', value)}
                                        options={QUEUE_OPTIONS.map((value) => [value, t(value)])}
                                    />
                                )}
                                {service === 'documents' && (
                                    <div className="grid gap-4 sm:grid-cols-2">
                                        <TextField
                                            label={t('Purok or Zone')}
                                            value={form.walkin_purok}
                                            onChange={(value) => setValue('walkin_purok', value)}
                                            maxLength={100}
                                        />
                                        <SelectField
                                            label={t('Document Type')}
                                            value={form.document_type}
                                            onChange={(value) => setValue('document_type', value)}
                                            options={DOCUMENT_OPTIONS.map((value) => [value, t(value)])}
                                        />
                                        <div className="sm:col-span-2">
                                            <TextField
                                                label={t('Purpose')}
                                                value={form.purpose}
                                                onChange={(value) => setValue('purpose', value)}
                                                required
                                                maxLength={500}
                                            />
                                        </div>
                                    </div>
                                )}
                                {service === 'reports' && (
                                    <>
                                        <TextField
                                            label={t('Name (optional)')}
                                            value={form.walkin_name}
                                            onChange={(value) => setValue('walkin_name', value)}
                                            maxLength={255}
                                        />
                                        <SelectField
                                            label={t('Category')}
                                            value={form.category}
                                            onChange={(value) => setValue('category', value)}
                                            options={CATEGORY_OPTIONS.map(([value, label]) => [value, t(label)])}
                                        />
                                        <TextField label={t('Report title')} value={form.title} onChange={(value) => setValue('title', value)} required maxLength={255} />
                                        <label className="block text-sm font-semibold text-slate-800">
                                            {t('What happened?')}
                                            <textarea required minLength={10} maxLength={5000} rows={4} value={form.description} onChange={(event) => setValue('description', event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm font-normal" />
                                        </label>
                                        <TextField label={t('Where did it happen?')} value={form.location} onChange={(value) => setValue('location', value)} required maxLength={255} />
                                    </>
                                )}

                                <div className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm leading-6 text-sky-950">
                                    <p className="font-bold">{t('Privacy notice')}</p>
                                    <p className="mt-1">{t('The information you enter and the service details will be recorded so staff at the selected Barangay can process this submission. Only authorized Barangay staff can view it. Do not enter a password or upload an ID on this shared kiosk. Ask staff if you have questions about privacy or records.')}</p>
                                </div>
                                <label className="flex min-h-12 items-start gap-3 rounded-xl border border-slate-200 p-3 text-sm leading-6">
                                    <input
                                        type="checkbox"
                                        required
                                        checked={form.privacy_acknowledged}
                                        onChange={(event) => setValue('privacy_acknowledged', event.target.checked)}
                                        className="mt-1 h-4 w-4 accent-primary"
                                    />
                                    <span>{t('I have read the privacy notice and agree to submit this request.')}</span>
                                </label>
                                {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
                                <div className="flex flex-wrap gap-3 pt-2">
                                    <button type="submit" disabled={submitting || directoryLoading || !barangayId} className="inline-flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-bold text-white hover:brightness-110 disabled:cursor-wait disabled:opacity-60">
                                        {submitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
                                        {t('Submit request')}
                                    </button>
                                    <button type="button" onClick={resetKiosk} className="min-h-12 rounded-xl border border-slate-300 px-5 font-semibold text-slate-700 hover:bg-slate-50">
                                        {t('Clear form')}
                                    </button>
                                </div>
                            </form>
                        </>
                    )}

                    {result && (
                        <div role="status" aria-live="polite" className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 text-center">
                            <ShieldCheck className="mx-auto h-12 w-12 text-emerald-700" aria-hidden="true" />
                            <h3 className="mt-3 text-xl font-extrabold text-emerald-950">{t('Request submitted')}</h3>
                            <p className="mt-2 text-sm text-emerald-900">{t('Keep this reference and give it to Barangay staff when asked.')}</p>
                            <p className="mt-4 text-xs font-bold uppercase tracking-wider text-emerald-800">{t('Reference number')}</p>
                            <p className="mt-1 text-3xl font-black tracking-wide text-emerald-950">{result.reference}</p>
                            <p className="mt-3 text-sm text-emerald-900">{t('Your request is waiting for Barangay staff review.')}</p>
                            <button type="button" onClick={resetKiosk} className="mt-6 min-h-12 rounded-xl bg-emerald-800 px-6 font-bold text-white hover:bg-emerald-900">{t('Done')}</button>
                        </div>
                    )}
                </section>

                <aside className="space-y-5">
                    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                        <div className="flex items-center gap-3">
                            <UsersRound className="h-5 w-5 text-primary" aria-hidden="true" />
                            <h2 className="font-extrabold">{t('Need an account?')}</h2>
                        </div>
                        <p className="mt-3 text-sm leading-6 text-slate-600">{t('Continue registration on your own phone. This kiosk does not collect passwords or identity documents.')}</p>
                        <div className="mt-4 flex justify-center rounded-xl bg-white p-3" aria-label={t('Scan this code to register on your own device')}>
                            <QRCodeSVG value={registrationUrl} size={176} level="M" includeMargin />
                        </div>
                        <p className="mt-3 text-center text-sm font-semibold text-slate-700">{t('Use your phone camera to scan the code.')}</p>
                    </section>
                    <p className="rounded-xl bg-slate-100 p-4 text-xs leading-5 text-slate-600">
                        {t('For your privacy, this screen clears after two minutes without activity. Please do not leave the kiosk while your information is visible.')}
                    </p>
                    {selectedBarangay && <p className="text-center text-xs text-slate-500">{t('Selected Barangay')}: {selectedBarangay.name}</p>}
                </aside>
            </div>
        </main>
    );
}

function TextField({
    label,
    value,
    onChange,
    required = false,
    maxLength,
}: {
    label: string;
    value: string;
    onChange: (value: string) => void;
    required?: boolean;
    maxLength?: number;
}) {
    return (
        <label className="block text-sm font-semibold text-slate-800">
            {label}
            <input required={required} maxLength={maxLength} value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 px-3 text-sm font-normal" />
        </label>
    );
}

function SelectField({
    label,
    value,
    onChange,
    options,
}: {
    label: string;
    value: string;
    onChange: (value: string) => void;
    options: readonly (readonly [string, string])[];
}) {
    return (
        <label className="block text-sm font-semibold text-slate-800">
            {label}
            <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal">
                {options.map(([optionValue, optionLabel]) => <option key={optionValue} value={optionValue}>{optionLabel}</option>)}
            </select>
        </label>
    );
}
