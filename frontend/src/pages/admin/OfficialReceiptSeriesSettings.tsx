import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { axiosPrivate } from '../../api/axios';
import { InlineErrorState } from '../../components/ui/InlineErrorState';

interface ReceiptSeries {
    configured: boolean;
    prefix: string;
    next_number: number | string | null;
    number_width: number;
    last_issued_number: number | null;
}

const inputClass = 'mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm';
const maxReceiptSerial = '9223372036854775807';

export function OfficialReceiptSeriesSettings() {
    const [series, setSeries] = useState<ReceiptSeries>({
        configured: false,
        prefix: '',
        next_number: null,
        number_width: 0,
        last_issued_number: null,
    });
    const [nextNumber, setNextNumber] = useState('');
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [retrying, setRetrying] = useState(false);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');
    const [messageIsError, setMessageIsError] = useState(false);
    const originalPrefix = useRef('');

    const loadSeries = useCallback(async (retry = false) => {
        if (retry) setRetrying(true);
        try {
            const response = await axiosPrivate.get('/official-receipt-series/');
            const data = response.data as ReceiptSeries;
            setSeries(data);
            originalPrefix.current = data.prefix;
            setNextNumber(data.next_number == null ? '' : String(data.next_number));
            setLoadError(false);
        } catch {
            setLoadError(true);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    }, []);

    useEffect(() => { void loadSeries(); }, [loadSeries]);

    const save = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const prefixChanged = series.last_issued_number != null &&
            series.prefix.trim() !== originalPrefix.current;
        if (prefixChanged && !window.confirm('You are starting a new O.R. series. Confirm the new prefix and next unused serial against the Barangay receipt book.')) {
            return;
        }
        setSaving(true);
        setMessage('');
        setMessageIsError(false);
        try {
            if (!/^[1-9]\d{0,18}$/.test(nextNumber) ||
                (nextNumber.length === 19 && nextNumber > maxReceiptSerial)) {
                setMessage('Enter a positive whole serial number within the supported range.');
                setMessageIsError(true);
                return;
            }
            const response = await axiosPrivate.patch('/official-receipt-series/', {
                prefix: series.prefix.trim(),
                next_number: nextNumber,
                number_width: Number(series.number_width),
            });
            setSeries(response.data as ReceiptSeries);
            originalPrefix.current = response.data.prefix;
            setNextNumber(String(response.data.next_number));
            setMessage('Approved receipt series saved. The next number is assigned only after staff confirms payment.');
        } catch (error: any) {
            const data = error?.response?.data;
            const detail = data?.detail || data?.prefix?.[0] || data?.next_number?.[0] || data?.number_width?.[0];
            setMessage(detail || 'Could not save the O.R. series. Check the values and try again.');
            setMessageIsError(true);
        } finally {
            setSaving(false);
        }
    };

    const serialPreview = /^[1-9]\d*$/.test(nextNumber)
        ? `${series.prefix}${nextNumber.padStart(series.number_width, '0')}`
        : '';

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-bold text-slate-900">Official Receipt (O.R.) series</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
                Configure the exact prefix and next unused serial from the Barangay-approved receipt book. KapitBayan assigns the next number when authorized staff confirms payment; a transfer reference or uploaded proof alone never issues an O.R.
            </p>
            {message && (
                <p role="status" className={`mt-4 rounded-lg p-3 text-sm ${messageIsError ? 'bg-rose-50 text-rose-800' : 'bg-emerald-50 text-emerald-800'}`}>
                    {message}
                </p>
            )}
            {loadError && (
                <div className="mt-4">
                    <InlineErrorState message="Could not load the O.R. series." onRetry={() => void loadSeries(true)} retrying={retrying} />
                </div>
            )}
            {loading ? <p className="mt-4 text-sm text-slate-500">Loading O.R. series…</p> : !loadError && (
                <form onSubmit={save} className="mt-5 grid gap-4 sm:grid-cols-3">
                    <label className="text-sm font-medium text-slate-700 sm:col-span-3">
                        Approved O.R. prefix
                        <input
                            className={inputClass}
                            value={series.prefix}
                            onChange={(event) => setSeries((current) => ({ ...current, prefix: event.target.value }))}
                            maxLength={40}
                            required
                            placeholder="Enter the exact prefix from your receipt book"
                        />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                        Next unused serial
                        <input
                            className={inputClass}
                            type="text"
                            inputMode="numeric"
                            maxLength={19}
                            value={nextNumber}
                            onChange={(event) => setNextNumber(event.target.value.replace(/\D/g, ''))}
                            required
                            placeholder="Enter the next serial"
                        />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                        Serial digit width
                        <input
                            className={inputClass}
                            type="number"
                            min="0"
                            max="12"
                            step="1"
                            value={series.number_width}
                            onChange={(event) => setSeries((current) => ({ ...current, number_width: Number(event.target.value) }))}
                            required
                        />
                        <span className="mt-1 block text-xs font-normal text-slate-500">Use 0 for no leading zeroes. After a series has issued a number, change the prefix to start a new approved series before changing its width.</span>
                    </label>
                    <div className="flex items-end">
                        <button type="submit" disabled={saving} className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground disabled:opacity-50">
                            {saving ? 'Saving…' : 'Save O.R. series'}
                        </button>
                    </div>
                    <p className="text-xs text-slate-500 sm:col-span-3">
                        {series.last_issued_number == null
                            ? 'No O.R. has been assigned by this series yet.'
                            : `Last issued serial: ${series.last_issued_number}. Prefix and digit width are locked to protect the series; the next serial can only move forward.`}
                    </p>
                    {serialPreview && (
                        <p className="text-sm font-semibold text-slate-700 sm:col-span-3">
                            Next-number preview: <span className="font-mono">{serialPreview}</span> <span className="text-xs font-normal text-slate-500">(preview only; assigned when payment is confirmed)</span>
                        </p>
                    )}
                </form>
            )}
        </section>
    );
}
