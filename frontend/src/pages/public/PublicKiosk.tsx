import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { AlertTriangle, FileText, Loader2, Package, Printer, ShieldCheck, TicketCheck, UsersRound } from 'lucide-react';
import { LanguageSwitcher } from '../../components/language/LanguageSwitcher';
import { useLanguage } from '../../context/language-context';
import { resolveApiBaseUrl } from '../../api/axios';

type Service = 'queue' | 'documents' | 'equipment' | 'reports';
type PublicBarangay = { id: number; name: string; municipality: string; province: string };
type SubmissionResult = {
    reference: string;
    status: string;
    service: Service;
    name?: string;
    detail?: string;
    timestamp?: string;
};

const INITIAL_FORM = {
    walkin_name: '',
    walkin_purok: '',
    walkin_contact: '',
    service_type: 'Document Processing & Clearances',
    document_type: 'Barangay Clearance',
    item_type: 'Monoblock Chairs',
    quantity: 1,
    borrow_date: new Date().toISOString().split('T')[0],
    return_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
    time_slot: '',
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

const EQUIPMENT_OPTIONS = [
    'Monoblock Chairs',
    'Tent / Canopy',
    'Sound System',
    'Tables',
    'Covered Court / Multi-Purpose Hall',
    'Other',
] as const;

const QUEUE_OPTIONS = [
    'Document Processing & Clearances',
    'Barangay ID Application',
    'Certificate of Indigency',
    'Equipment & Facility Borrowing',
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
            equipment: 'equipment',
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
        } else if (service === 'equipment') {
            payload = {
                ...common,
                walkin_name: form.walkin_name,
                walkin_contact: form.walkin_contact,
                item_type: form.item_type,
                quantity: Number(form.quantity) || 1,
                borrow_date: form.borrow_date,
                return_date: form.return_date,
                time_slot: form.time_slot,
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
            const detailText =
                service === 'queue'
                    ? form.service_type
                    : service === 'documents'
                      ? form.document_type
                      : service === 'equipment'
                        ? `${form.item_type} (${form.quantity}x)`
                        : form.title;
            const nowTime = new Date().toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                hour12: true,
            });
            setResult({
                reference: body.reference,
                status: body.status,
                service,
                name: form.walkin_name.trim(),
                detail: detailText,
                timestamp: nowTime,
            });
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
        { id: 'equipment', label: t('Borrow Equipment'), icon: <Package aria-hidden="true" /> },
        { id: 'reports', label: t('Report an Issue'), icon: <AlertTriangle aria-hidden="true" /> },
    ];

    return (
        <main className="min-h-screen bg-slate-50 text-slate-900 print:bg-white print:p-0">
            <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4 sm:px-8 print:hidden">
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

            <div className="mx-auto grid max-w-6xl gap-6 px-4 py-6 sm:px-8 lg:grid-cols-[minmax(0,1fr)_280px] lg:py-10 print:block print:max-w-xl print:p-0">
                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8 print:border-none print:p-0 print:shadow-none">
                    {!result && (
                        <>
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
                        </>
                    )}

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
                            <div className="mb-6 grid gap-2 sm:grid-cols-2 lg:grid-cols-4" role="tablist" aria-label={t('Choose a service')}>
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
                                {service === 'equipment' && (
                                    <div className="grid gap-4 sm:grid-cols-2">
                                        <TextField
                                            label={t('Contact number or Purok')}
                                            value={form.walkin_contact}
                                            onChange={(value) => setValue('walkin_contact', value)}
                                            maxLength={100}
                                        />
                                        <SelectField
                                            label={t('Equipment or Facility')}
                                            value={form.item_type}
                                            onChange={(value) => setValue('item_type', value)}
                                            options={EQUIPMENT_OPTIONS.map((value) => [value, t(value)])}
                                        />
                                        <div>
                                            <label className="block text-sm font-semibold text-slate-800">
                                                {t('Quantity / Units')}
                                                <input
                                                    type="number"
                                                    min={1}
                                                    max={500}
                                                    required
                                                    value={form.quantity}
                                                    onChange={(event) => setValue('quantity', event.target.value)}
                                                    className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal"
                                                />
                                            </label>
                                        </div>
                                        <TextField
                                            label={t('Time slot / Hours (optional)')}
                                            value={form.time_slot}
                                            onChange={(value) => setValue('time_slot', value)}
                                            maxLength={100}
                                            placeholder="e.g. 8:00 AM - 5:00 PM"
                                        />
                                        <div>
                                            <label className="block text-sm font-semibold text-slate-800">
                                                {t('Borrow date')}
                                                <input
                                                    type="date"
                                                    required
                                                    value={form.borrow_date}
                                                    onChange={(event) => setValue('borrow_date', event.target.value)}
                                                    className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal"
                                                />
                                            </label>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-semibold text-slate-800">
                                                {t('Return date')}
                                                <input
                                                    type="date"
                                                    required
                                                    min={form.borrow_date}
                                                    value={form.return_date}
                                                    onChange={(event) => setValue('return_date', event.target.value)}
                                                    className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal"
                                                />
                                            </label>
                                        </div>
                                        <div className="sm:col-span-2">
                                            <TextField
                                                label={t('Purpose of borrowing')}
                                                value={form.purpose}
                                                onChange={(value) => setValue('purpose', value)}
                                                required
                                                maxLength={500}
                                                placeholder="e.g. Community meeting, sports event, family assembly"
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
                        <div role="status" aria-live="polite" className="kiosk-print-slip rounded-2xl border border-emerald-200 bg-emerald-50 p-6 text-center print:border print:border-slate-800 print:bg-white print:p-8 print:shadow-none">
                            <ShieldCheck className="mx-auto h-12 w-12 text-emerald-700 print:hidden" aria-hidden="true" />
                            <div className="kiosk-print-header hidden print:block print:mb-4 print:border-b print:border-slate-300 print:pb-3">
                                <p className="text-xs font-bold tracking-widest text-slate-500 uppercase">KapitBayan</p>
                                <h2 className="text-xl font-black text-slate-900">{selectedBarangay?.name || t('Barangay Public Service Kiosk')}</h2>
                                <p className="text-xs text-slate-600">{selectedBarangay ? `${selectedBarangay.municipality}, ${selectedBarangay.province}` : ''}</p>
                                <p className="mt-1 text-[11px] text-slate-500 font-mono">{t('Public Walk-in Slip')} • {result.timestamp || new Date().toLocaleTimeString()}</p>
                            </div>
                            <h3 className="mt-3 text-xl font-extrabold text-emerald-950 print:hidden">{t('Request submitted')}</h3>
                            <p className="mt-2 text-sm text-emerald-900 print:hidden">{t('Keep this reference and give it to Barangay staff when asked.')}</p>

                            <div className="my-4 rounded-xl border border-dashed border-emerald-300 bg-white p-5 shadow-sm print:my-3 print:border-2 print:border-slate-800 print:p-6 print:shadow-none">
                                <p className="text-xs font-bold uppercase tracking-wider text-emerald-800 print:text-slate-600">{t('Reference number')}</p>
                                <p className="mt-1 font-mono text-4xl font-black tracking-wider text-emerald-950 print:text-5xl print:text-slate-950">{result.reference}</p>
                                {result.name && (
                                    <p className="mt-3 text-sm font-bold text-slate-800 print:text-base">{t('Applicant')}: {result.name}</p>
                                )}
                                {result.detail && (
                                    <p className="text-xs text-slate-600 print:text-sm">{t('Service')}: {result.detail}</p>
                                )}
                                {result.timestamp && (
                                    <p className="mt-1 text-[11px] text-slate-400 print:hidden">{t('Time Issued')}: {result.timestamp}</p>
                                )}
                            </div>

                            <p className="mt-2 text-xs text-emerald-800 print:hidden">
                                {t('Take a photo with your phone or click "Print Slip" to keep a paper ticket copy.')}
                            </p>
                            <p className="kiosk-print-footer hidden print:block print:mt-4 print:text-xs print:font-semibold print:text-slate-700">
                                {t('Please present this slip at the Barangay service counter when your reference is called.')}
                            </p>

                            <div className="mt-6 flex flex-wrap items-center justify-center gap-3 print:hidden">
                                <button
                                    type="button"
                                    onClick={() => window.print()}
                                    className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-slate-900 px-6 font-bold text-white shadow hover:bg-slate-800 transition-colors cursor-pointer"
                                    aria-label={t('Print Walk-in Ticket Slip')}
                                >
                                    <Printer className="h-4 w-4" aria-hidden="true" />
                                    {t('Print Slip')}
                                </button>
                                <button
                                    type="button"
                                    onClick={resetKiosk}
                                    className="min-h-12 rounded-xl bg-emerald-800 px-6 font-bold text-white shadow hover:bg-emerald-900 transition-colors"
                                >
                                    {t('Done')}
                                </button>
                            </div>
                        </div>
                    )}
                </section>

                <aside className="space-y-5 print:hidden">
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
    placeholder,
}: {
    label: string;
    value: string;
    onChange: (value: string) => void;
    required?: boolean;
    maxLength?: number;
    placeholder?: string;
}) {
    return (
        <label className="block text-sm font-semibold text-slate-800">
            {label}
            <input
                required={required}
                maxLength={maxLength}
                placeholder={placeholder}
                value={value}
                onChange={(event) => onChange(event.target.value)}
                className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 px-3 text-sm font-normal"
            />
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
