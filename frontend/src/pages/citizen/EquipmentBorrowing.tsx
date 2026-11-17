import React, { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import {
    Calendar,
    CheckCircle2,
    Clock3,
    Loader2,
    Package,
    Plus,
    RotateCcw,
    Send,
    X,
    XCircle,
} from 'lucide-react';
import { axiosPrivate } from '../../api/axios';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { useAuth } from '../../context/auth-context';
import { useLanguage } from '../../context/language-context';
import { useModalFocus } from '../../hooks/useModalFocus';

export interface EquipmentBorrowRequest {
    id: number;
    resident_name: string;
    is_walkin?: boolean;
    walkin_contact?: string;
    walkin_purok?: string;
    borrower_id_type?: string;
    kiosk_auth_method?: string;
    item_type: string;
    quantity: number;
    borrow_date: string;
    return_date: string;
    time_slot: string;
    purpose: string;
    status: 'PENDING' | 'APPROVED' | 'DECLINED' | 'RETURNED';
    admin_notes: string;
    reviewed_by_name?: string | null;
    reviewed_at?: string | null;
    returned_at?: string | null;
    created_at: string;
}

const equipmentItemTypes = [
    'Monoblock Chairs',
    'Tent / Canopy',
    'Sound System',
    'Tables',
    'Covered Court / Multi-Purpose Hall',
    'Other',
];

const statusLabel: Record<EquipmentBorrowRequest['status'], string> = {
    PENDING: 'Pending',
    APPROVED: 'Approved',
    DECLINED: 'Declined',
    RETURNED: 'Returned',
};

const statusBadgeStyle: Record<EquipmentBorrowRequest['status'], string> = {
    PENDING: 'bg-amber-50 text-amber-800 border-amber-200',
    APPROVED: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    DECLINED: 'bg-rose-50 text-rose-800 border-rose-200',
    RETURNED: 'bg-slate-100 text-slate-700 border-slate-300',
};

type StatusFilter = 'ALL' | EquipmentBorrowRequest['status'];

export const EquipmentBorrowing: React.FC = () => {
    const { user } = useAuth();
    const isStaff = user?.role === 'ADMIN';
    const { t } = useLanguage();
    const text = (source: string) => t(source);

    const [requests, setRequests] = useState<EquipmentBorrowRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [retrying, setRetrying] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [reviewingId, setReviewingId] = useState<number | null>(null);
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL');

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [itemType, setItemType] = useState(equipmentItemTypes[0]);
    const [quantity, setQuantity] = useState<number>(1);
    const [borrowDate, setBorrowDate] = useState('');
    const [returnDate, setReturnDate] = useState('');
    const [timeSlot, setTimeSlot] = useState('08:00 AM - 05:00 PM');
    const [purpose, setPurpose] = useState('');
    const [formError, setFormError] = useState<string | null>(null);

    const [notes, setNotes] = useState<Record<number, string>>({});

    const modalRef = useModalFocus<HTMLDivElement>(isModalOpen, () => {
        if (!submitting) setIsModalOpen(false);
    });

    const loadRequests = async (isRetry = false) => {
        if (isRetry) setRetrying(true);
        try {
            const response = await axiosPrivate.get('/equipment-requests/');
            const data = response.data.results || response.data;
            setRequests(Array.isArray(data) ? data : []);
            setLoadError(false);
        } catch {
            setLoadError(true);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    };

    useEffect(() => {
        void loadRequests();
    }, []);

    const filteredRequests = useMemo(() => {
        if (statusFilter === 'ALL') return requests;
        return requests.filter((req) => req.status === statusFilter);
    }, [requests, statusFilter]);

    const resetForm = () => {
        setItemType(equipmentItemTypes[0]);
        setQuantity(1);
        setBorrowDate('');
        setReturnDate('');
        setTimeSlot('08:00 AM - 05:00 PM');
        setPurpose('');
        setFormError(null);
    };

    const submitRequest = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setFormError(null);

        if (!borrowDate || !returnDate) {
            setFormError(text('Please select both borrow and return dates.'));
            return;
        }
        const todayLocal = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().split('T')[0];
        if (borrowDate < todayLocal) {
            setFormError(text('Borrow date cannot be in the past.'));
            return;
        }
        if (returnDate < borrowDate) {
            setFormError(text('Return date must be on or after the borrow date.'));
            return;
        }
        if (quantity < 1) {
            setFormError(text('Quantity must be at least 1.'));
            return;
        }
        if (!purpose.trim()) {
            setFormError(text('Please provide the purpose for borrowing.'));
            return;
        }

        setSubmitting(true);
        try {
            await axiosPrivate.post('/equipment-requests/', {
                item_type: itemType,
                quantity,
                borrow_date: borrowDate,
                return_date: returnDate,
                time_slot: timeSlot.trim(),
                purpose: purpose.trim(),
            });
            resetForm();
            setIsModalOpen(false);
            toast.success(text('Equipment borrowing request submitted for review.'));
            await loadRequests();
        } catch (error: any) {
            const apiError =
                error.response?.data?.borrow_date?.[0] ||
                error.response?.data?.return_date?.[0] ||
                error.response?.data?.detail ||
                text('Could not submit your borrowing request.');
            setFormError(apiError);
            toast.error(apiError);
        } finally {
            setSubmitting(false);
        }
    };

    const reviewRequest = async (
        request: EquipmentBorrowRequest,
        status: EquipmentBorrowRequest['status'],
    ) => {
        const adminNotes = (notes[request.id] ?? request.admin_notes ?? '').trim();
        if (status === 'DECLINED' && !adminNotes) {
            toast.error(text('Add a reason before declining this borrowing request.'));
            return;
        }
        setReviewingId(request.id);
        try {
            const response = await axiosPrivate.patch(`/equipment-requests/${request.id}/`, {
                status,
                admin_notes: adminNotes,
            });
            setRequests((current) =>
                current.map((item) =>
                    item.id === request.id ? { ...item, ...response.data } : item,
                ),
            );
            toast.success(text(`Request marked ${statusLabel[status].toLowerCase()}.`));
        } catch (error: any) {
            const detail =
                error.response?.data?.admin_notes?.[0] ||
                error.response?.data?.status?.[0] ||
                error.response?.data?.detail ||
                text('Could not update this borrowing request.');
            toast.error(detail);
        } finally {
            setReviewingId(null);
        }
    };

    return (
        <section className="space-y-6">
            <header className="rounded-2xl border border-slate-200 bg-white p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                        <Package className="mt-1 h-6 w-6 text-primary-text" aria-hidden="true" />
                        <div>
                            <h1 className="text-2xl font-bold text-slate-900">
                                {text(
                                    isStaff
                                        ? 'Equipment & Facility Borrowing Management'
                                        : 'Equipment & Facility Borrowing',
                                )}
                            </h1>
                            <p className="mt-1 max-w-3xl text-sm text-slate-600">
                                {text(
                                    isStaff
                                        ? 'Review resident borrowing requests for your barangay, record approval or decline remarks, and track returned items.'
                                        : 'Borrow barangay chairs, tents, tables, sound systems, or reserve community facilities. Requests are reviewed manually by barangay staff.',
                                )}
                            </p>
                        </div>
                    </div>

                    {!isStaff && (
                        <button
                            type="button"
                            onClick={() => {
                                setFormError(null);
                                setIsModalOpen(true);
                            }}
                            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-xs transition hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        >
                            <Plus className="h-4 w-4" aria-hidden="true" />
                            {text('Request Equipment or Facility')}
                        </button>
                    )}
                </div>
            </header>

            {isModalOpen && !isStaff && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
                    <div
                        ref={modalRef}
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="equipment-borrow-modal-title"
                        tabIndex={-1}
                        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
                    >
                        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                            <h2 id="equipment-borrow-modal-title" className="text-lg font-bold text-slate-900">
                                {text('New Borrowing Request')}
                            </h2>
                            <button
                                type="button"
                                onClick={() => setIsModalOpen(false)}
                                aria-label={text('Close borrowing request modal')}
                                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                            >
                                <X className="h-5 w-5" aria-hidden="true" />
                            </button>
                        </div>

                        <form onSubmit={submitRequest} className="mt-4 space-y-4">
                            {formError && (
                                <div
                                    role="alert"
                                    className="rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-800"
                                >
                                    {formError}
                                </div>
                            )}

                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                                <label className="block text-sm font-medium text-slate-700 sm:col-span-2">
                                    {text('Item or facility')}
                                    <select
                                        value={itemType}
                                        onChange={(e) => setItemType(e.target.value)}
                                        className="mt-1 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm"
                                    >
                                        {equipmentItemTypes.map((type) => (
                                            <option key={type} value={type}>
                                                {text(type)}
                                            </option>
                                        ))}
                                    </select>
                                </label>

                                <label className="block text-sm font-medium text-slate-700">
                                    {text('Quantity')}
                                    <input
                                        type="number"
                                        min={1}
                                        max={500}
                                        required
                                        value={quantity}
                                        onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))}
                                        className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                                    />
                                </label>
                            </div>

                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                <label className="block text-sm font-medium text-slate-700">
                                    {text('Borrow date')}
                                    <input
                                        type="date"
                                        required
                                        min={new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().split('T')[0]}
                                        value={borrowDate}
                                        onChange={(e) => setBorrowDate(e.target.value)}
                                        className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                                    />
                                </label>

                                <label className="block text-sm font-medium text-slate-700">
                                    {text('Return date')}
                                    <input
                                        type="date"
                                        required
                                        value={returnDate}
                                        onChange={(e) => setReturnDate(e.target.value)}
                                        className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                                    />
                                </label>
                            </div>

                            <label className="block text-sm font-medium text-slate-700">
                                {text('Time slot')}
                                <input
                                    type="text"
                                    maxLength={100}
                                    value={timeSlot}
                                    onChange={(e) => setTimeSlot(e.target.value)}
                                    placeholder={text('e.g. 08:00 AM - 05:00 PM')}
                                    className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                                />
                            </label>

                            <label className="block text-sm font-medium text-slate-700">
                                {text('Purpose')}
                                <textarea
                                    required
                                    rows={3}
                                    maxLength={2000}
                                    value={purpose}
                                    onChange={(e) => setPurpose(e.target.value)}
                                    placeholder={text('Describe the event or purpose for borrowing.')}
                                    className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                                />
                            </label>

                            <div className="flex justify-end gap-2 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setIsModalOpen(false)}
                                    className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                                >
                                    {text('Cancel')}
                                </button>
                                <button
                                    type="submit"
                                    disabled={submitting}
                                    className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
                                >
                                    {submitting ? (
                                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                                    ) : (
                                        <Send className="h-4 w-4" aria-hidden="true" />
                                    )}
                                    {text('Submit Borrowing Request')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="font-semibold text-slate-900">
                        {text(isStaff ? 'Borrowing requests for your barangay' : 'Your borrowing requests')}
                    </h2>

                    <div
                        role="group"
                        aria-label={text('Filter requests by status')}
                        className="flex flex-wrap gap-1.5"
                    >
                        {(['ALL', 'PENDING', 'APPROVED', 'DECLINED', 'RETURNED'] as StatusFilter[]).map(
                            (status) => (
                                <button
                                    key={status}
                                    type="button"
                                    onClick={() => setStatusFilter(status)}
                                    aria-pressed={statusFilter === status}
                                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                                        statusFilter === status
                                            ? 'bg-primary text-primary-foreground'
                                            : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                                    }`}
                                >
                                    {status === 'ALL' ? text('All') : text(statusLabel[status])}
                                </button>
                            ),
                        )}
                    </div>
                </div>

                {loading ? (
                    <div className="flex items-center gap-2 rounded-xl bg-white p-6 text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />{' '}
                        {text('Loading borrowing requests…')}
                    </div>
                ) : loadError ? (
                    <InlineErrorState
                        message={text("We couldn't load equipment borrowing requests.")}
                        onRetry={() => void loadRequests(true)}
                        retrying={retrying}
                    />
                ) : filteredRequests.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
                        {text('No equipment borrowing requests found.')}
                    </div>
                ) : (
                    filteredRequests.map((request) => {
                        const canReview =
                            isStaff &&
                            (request.status === 'PENDING' || request.status === 'APPROVED');
                        return (
                            <article
                                key={request.id}
                                className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5"
                            >
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div>
                                        <h3 className="font-semibold text-slate-900">
                                            {text(request.item_type)}{' '}
                                            <span className="text-sm font-normal text-slate-600">
                                                (x{request.quantity})
                                            </span>
                                        </h3>
                                        <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                                            {isStaff && (
                                                <span className="font-medium text-slate-700">
                                                    {request.resident_name} ·
                                                </span>
                                            )}
                                            <span className="inline-flex items-center gap-1">
                                                <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
                                                {request.borrow_date} → {request.return_date}
                                            </span>
                                            {request.time_slot && (
                                                <span>({request.time_slot})</span>
                                            )}
                                        </p>
                                    </div>
                                    <span
                                        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${statusBadgeStyle[request.status]}`}
                                    >
                                        {request.status === 'APPROVED' ? (
                                            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                                        ) : request.status === 'DECLINED' ? (
                                            <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
                                        ) : request.status === 'RETURNED' ? (
                                            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                                        ) : (
                                            <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                                        )}
                                        {text(statusLabel[request.status])}
                                    </span>
                                </div>

                                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                                    {request.purpose}
                                </p>

                                {isStaff && (request.walkin_contact || request.walkin_purok || request.borrower_id_type || request.kiosk_auth_method) && (
                                    <div className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                                        {request.kiosk_auth_method && (
                                            <span className="rounded-md bg-sky-100 px-2 py-0.5 font-semibold text-sky-900">
                                                {request.kiosk_auth_method === 'STAFF_PIN'
                                                    ? text('Kiosk: Staff PIN Verified')
                                                    : request.kiosk_auth_method === 'RESIDENT_VERIFIED'
                                                      ? text('Kiosk: Resident Account Verified')
                                                      : request.kiosk_auth_method}
                                            </span>
                                        )}
                                        {request.walkin_contact && (
                                            <span><strong>{text('Contact')}:</strong> {request.walkin_contact}</span>
                                        )}
                                        {request.walkin_purok && (
                                            <span><strong>{text('Purok/Address')}:</strong> {request.walkin_purok}</span>
                                        )}
                                        {request.borrower_id_type && (
                                            <span><strong>{text('ID Presented')}:</strong> {request.borrower_id_type}</span>
                                        )}
                                    </div>
                                )}

                                {request.admin_notes && (
                                    <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                                        <span className="font-semibold">
                                            {text('Admin remarks: ')}
                                        </span>
                                        {request.admin_notes}
                                    </p>
                                )}

                                {canReview && (
                                    <div className="space-y-3 border-t border-slate-100 pt-4">
                                        <label className="block text-sm font-medium text-slate-700">
                                            {text('Admin remarks')}
                                            <textarea
                                                rows={2}
                                                maxLength={2000}
                                                value={notes[request.id] ?? request.admin_notes}
                                                onChange={(event) =>
                                                    setNotes((current) => ({
                                                        ...current,
                                                        [request.id]: event.target.value,
                                                    }))
                                                }
                                                className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
                                                placeholder={text(
                                                    'Add pickup instructions, return notes, or reason if declining.',
                                                )}
                                            />
                                        </label>
                                        <div className="flex flex-wrap gap-2">
                                            {request.status === 'PENDING' && (
                                                <>
                                                    <button
                                                        type="button"
                                                        disabled={reviewingId === request.id}
                                                        onClick={() =>
                                                            void reviewRequest(request, 'APPROVED')
                                                        }
                                                        className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                                                    >
                                                        {text('Approve')}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        disabled={reviewingId === request.id}
                                                        onClick={() =>
                                                            void reviewRequest(request, 'DECLINED')
                                                        }
                                                        className="rounded-lg bg-rose-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                                                    >
                                                        {text('Decline')}
                                                    </button>
                                                </>
                                            )}
                                            {request.status === 'APPROVED' && (
                                                <button
                                                    type="button"
                                                    disabled={reviewingId === request.id}
                                                    onClick={() =>
                                                        void reviewRequest(request, 'RETURNED')
                                                    }
                                                    className="rounded-lg bg-slate-800 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                                                >
                                                    {text('Mark Returned')}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </article>
                        );
                    })
                )}
            </div>
        </section>
    );
};
