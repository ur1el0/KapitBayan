import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { axiosPrivate } from '../../api/axios';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { ShieldCheck, UserPlus, Users } from 'lucide-react';

export interface StaffMember {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
    full_name: string;
    role: string;
    is_active: boolean;
    date_joined: string;
    last_login: string | null;
}

const inputClass = 'mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base md:text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus:border-primary';

function getApiErrorMessage(error: unknown, fallback: string) {
    if (!error || typeof error !== 'object' || !('response' in error)) return fallback;
    const response = error as { response?: { data?: Record<string, unknown> } };
    const data = response.response?.data;
    if (!data || typeof data !== 'object') return fallback;

    const firstKey = Object.keys(data)[0];
    const value = data[firstKey];
    if (Array.isArray(value) && value.length > 0) return `${firstKey}: ${value[0]}`;
    if (typeof value === 'string') return value;
    return fallback;
}

export function StaffManagementSettings() {
    const [staffList, setStaffList] = useState<StaffMember[]>([]);
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [email, setEmail] = useState('');

    const [loading, setLoading] = useState(true);
    const [retrying, setRetrying] = useState(false);
    const [loadError, setLoadError] = useState(false);
    const [saving, setSaving] = useState(false);
    const [togglingId, setTogglingId] = useState<number | null>(null);
    const [editingStaffId, setEditingStaffId] = useState<number | null>(null);
    const [editValues, setEditValues] = useState<Pick<StaffMember, 'first_name' | 'last_name' | 'email'> | null>(null);
    const [editSaving, setEditSaving] = useState(false);
    const [editError, setEditError] = useState<string | null>(null);
    const editFirstNameInputRef = useRef<HTMLInputElement | null>(null);
    const editButtonRefs = useRef<Record<number, HTMLButtonElement | null>>({});
    const focusAfterEditTransitionId = useRef<number | null>(null);
    const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

    const loadStaff = useCallback(async (isRetry = false) => {
        if (isRetry) setRetrying(true);

        try {
            const response = await axiosPrivate.get('/auth/staff/');
            const data = response.data.results || response.data;
            setStaffList(Array.isArray(data) ? data : []);
            setLoadError(false);
        } catch {
            setLoadError(true);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    }, []);

    useEffect(() => {
        void loadStaff();
    }, [loadStaff]);

    useEffect(() => {
        const staffId = focusAfterEditTransitionId.current;
        if (staffId === null) return;

        if (editingStaffId === staffId) {
            editFirstNameInputRef.current?.focus();
        } else {
            editButtonRefs.current[staffId]?.focus();
        }
        focusAfterEditTransitionId.current = null;
    }, [editingStaffId]);

    const submit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setSaving(true);
        setMessage(null);

        try {
            const response = await axiosPrivate.post('/auth/staff/', {
                first_name: firstName.trim(),
                last_name: lastName.trim(),
                email: email.trim().toLowerCase(),
            });
            setStaffList((current) => [response.data, ...current]);
            setFirstName('');
            setLastName('');
            setEmail('');
            setMessage({
                text: `Field Official account created. Setup instructions are being sent to ${response.data.email}. If the email does not arrive or the link expires, they can use Forgot Password.`,
                type: 'success',
            });
        } catch (err: unknown) {
            setMessage({
                text: getApiErrorMessage(err, 'Could not create the Field Official account. Please check the inputs.'),
                type: 'error',
            });
        } finally {
            setSaving(false);
        }
    };

    const beginEdit = (staff: StaffMember) => {
        focusAfterEditTransitionId.current = staff.id;
        setMessage(null);
        setEditError(null);
        setEditingStaffId(staff.id);
        setEditValues({
            first_name: staff.first_name,
            last_name: staff.last_name,
            email: staff.email,
        });
    };

    const cancelEdit = (staffId: number) => {
        focusAfterEditTransitionId.current = staffId;
        setEditingStaffId(null);
        setEditValues(null);
        setEditError(null);
    };

    const submitEdit = async (event: FormEvent<HTMLFormElement>, staff: StaffMember) => {
        event.preventDefault();
        if (!editValues) return;

        setEditSaving(true);
        setEditError(null);
        try {
            const payload = {
                first_name: editValues.first_name.trim(),
                last_name: editValues.last_name.trim(),
                email: editValues.email.trim().toLowerCase(),
            };
            const response = await axiosPrivate.patch(`/auth/staff/${staff.id}/`, payload);
            setStaffList((current) =>
                current.map((item) => (item.id === staff.id ? response.data : item))
            );
            focusAfterEditTransitionId.current = staff.id;
            setEditingStaffId(null);
            setEditValues(null);
            setMessage({ text: `Profile updated for ${staff.email}.`, type: 'success' });
        } catch (error: unknown) {
            setEditError(getApiErrorMessage(error, 'Could not update this field official. Please review the details and try again.'));
        } finally {
            setEditSaving(false);
        }
    };

    const toggleStatus = async (staff: StaffMember) => {
        setTogglingId(staff.id);
        setMessage(null);
        try {
            const response = await axiosPrivate.post(`/auth/staff/${staff.id}/toggle-status/`);
            setStaffList((current) =>
                current.map((item) => (item.id === staff.id ? response.data : item))
            );
            setMessage({
                text: `Field Official ${staff.email} is now ${response.data.is_active ? 'active' : 'inactive'}.`,
                type: 'success',
            });
        } catch {
            setMessage({
                text: `Could not change status for ${staff.email}.`,
                type: 'error',
            });
        } finally {
            setTogglingId(null);
        }
    };

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
                <div className="rounded-lg bg-primary/10 p-2 text-primary">
                    <Users className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-slate-900">Barangay Field Officials & Staff</h2>
                    <p className="mt-0.5 text-sm leading-6 text-slate-600">
                        Create and manage Field Official accounts for your Barangay. They sign in with their official email, set a password through an emailed setup link, and use the mobile app for their work.
                    </p>
                </div>
            </div>

            <p className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3 text-sm leading-6 text-blue-900">
                Barangay Admin accounts are created by a platform operator after onboarding review. Use this page to create and manage Field Officials only.
            </p>

            {message && (
                <div
                    role="alert"
                    className={`mt-4 rounded-lg p-3 text-sm ${
                        message.type === 'success' ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800'
                    }`}
                >
                    {message.text}
                </div>
            )}

            <form onSubmit={submit} className="mt-6 rounded-lg border border-slate-100 bg-slate-50/50 p-5">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 mb-4">
                    <UserPlus className="h-4 w-4 text-primary" aria-hidden="true" />
                    <span>Add Field Official</span>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                    <label className="text-sm font-medium text-slate-700">
                        First Name
                        <input
                            className={inputClass}
                            value={firstName}
                            onChange={(e) => setFirstName(e.target.value)}
                            maxLength={150}
                            required
                            placeholder="e.g. Ricardo"
                        />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                        Last Name
                        <input
                            className={inputClass}
                            value={lastName}
                            onChange={(e) => setLastName(e.target.value)}
                            maxLength={150}
                            required
                            placeholder="e.g. Dalisay"
                        />
                    </label>
                    <label className="text-sm font-medium text-slate-700">
                        Official Email (sign-in)
                        <input
                            type="email"
                            className={inputClass}
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            maxLength={254}
                            required
                            placeholder="e.g. carding@barangay.gov.ph"
                        />
                    </label>
                    <button
                        type="submit"
                        disabled={saving}
                        className="min-h-11 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground outline-none disabled:opacity-50 hover:bg-primary/90 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 transition-colors sm:col-span-2"
                    >
                        {saving ? 'Creating Account…' : 'Register Field Official'}
                    </button>
                </div>
            </form>

            <div className="mt-8 space-y-3" aria-live="polite">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">
                    Barangay Field Personnel
                </h3>

                {loadError && (
                    <InlineErrorState
                        message="Could not load field officials list."
                        onRetry={() => void loadStaff(true)}
                        retrying={retrying}
                    />
                )}

                {loading ? (
                    <p className="text-sm text-slate-500">Loading registered personnel…</p>
                ) : !loadError && staffList.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center">
                        <ShieldCheck className="mx-auto h-8 w-8 text-slate-400" aria-hidden="true" />
                        <p className="mt-2 text-sm font-medium text-slate-700">No field officials registered yet</p>
                        <p className="mt-1 text-xs text-slate-500">
                            Use the form above to onboard Barangay Tanods and field inspectors for your jurisdiction.
                        </p>
                    </div>
                ) : (
                    <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 overflow-hidden">
                        {staffList.map((staff) => (
                            <article
                                key={staff.id}
                                className="bg-white p-4 hover:bg-slate-50/50 transition-colors"
                            >
                                {editingStaffId === staff.id && editValues ? (
                                    <form onSubmit={(event) => void submitEdit(event, staff)} className="space-y-4" aria-busy={editSaving}>
                                        <div className="flex flex-wrap items-center gap-2">
                                            <h4 className="font-semibold text-slate-900 text-sm">Edit {staff.full_name}</h4>
                                            <span className="text-xs text-slate-500">This Field Official signs in with {staff.email}.</span>
                                        </div>
                                        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                                            <label className="text-sm font-medium text-slate-700">
                                                First Name for {staff.full_name}
                                                <input
                                                    ref={editFirstNameInputRef}
                                                    className={inputClass}
                                                    value={editValues.first_name}
                                                    onChange={(event) => setEditValues({ ...editValues, first_name: event.target.value })}
                                                    disabled={editSaving}
                                                    maxLength={150}
                                                    required
                                                    autoComplete="given-name"
                                                />
                                            </label>
                                            <label className="text-sm font-medium text-slate-700">
                                                Last Name for {staff.full_name}
                                                <input
                                                    className={inputClass}
                                                    value={editValues.last_name}
                                                    onChange={(event) => setEditValues({ ...editValues, last_name: event.target.value })}
                                                    disabled={editSaving}
                                                    maxLength={150}
                                                    required
                                                    autoComplete="family-name"
                                                />
                                            </label>
                                            <label className="text-sm font-medium text-slate-700">
                                                Official Email (sign-in) for {staff.full_name}
                                                <input
                                                    type="email"
                                                    className={inputClass}
                                                    value={editValues.email}
                                                    onChange={(event) => setEditValues({ ...editValues, email: event.target.value })}
                                                    disabled={editSaving}
                                                    maxLength={254}
                                                    required
                                                    autoComplete="email"
                                                />
                                            </label>
                                        </div>
                                        {editError && <p role="alert" className="text-sm text-red-700">{editError}</p>}
                                        <div className="flex flex-wrap gap-2">
                                            <button
                                                type="submit"
                                                disabled={editSaving}
                                                className="min-h-11 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground outline-none transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                                            >
                                                {editSaving ? 'Saving…' : 'Save Changes'}
                                            </button>
                                            <button
                                                type="button"
                                                disabled={editSaving}
                                                onClick={() => cancelEdit(staff.id)}
                                                className="min-h-11 rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 outline-none transition-colors disabled:opacity-50 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    </form>
                                ) : (
                                    <div className="flex flex-wrap items-center justify-between gap-3">
                                        <div className="space-y-1">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <h4 className="font-semibold text-slate-900 text-sm">{staff.full_name}</h4>
                                                <span className="text-xs text-slate-500">{staff.email}</span>
                                                <span
                                                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                                        staff.is_active
                                                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                                            : 'bg-slate-100 text-slate-600 border border-slate-200'
                                                    }`}
                                                >
                                                    {staff.is_active ? 'Active' : 'Deactivated'}
                                                </span>
                                            </div>
                                            <p className="text-xs text-slate-500 break-all">{staff.email}</p>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            <button
                                                type="button"
                                                ref={(button) => { editButtonRefs.current[staff.id] = button; }}
                                                onClick={() => beginEdit(staff)}
                                                className="min-h-11 rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 outline-none transition-colors hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                                                aria-label={`Edit ${staff.full_name}`}
                                            >
                                                Edit
                                            </button>
                                            <button
                                                type="button"
                                                disabled={togglingId === staff.id}
                                                onClick={() => void toggleStatus(staff)}
                                                className={`min-h-11 min-w-11 rounded-md border px-3 py-1.5 text-xs font-semibold outline-none transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${
                                                    staff.is_active
                                                        ? 'border-red-200 text-red-700 hover:bg-red-50'
                                                        : 'border-emerald-200 text-emerald-700 hover:bg-emerald-50'
                                                }`}
                                            >
                                                {togglingId === staff.id
                                                    ? 'Updating…'
                                                    : staff.is_active
                                                    ? 'Deactivate'
                                                    : 'Activate'}
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </article>
                        ))}
                    </div>
                )}
            </div>

        </section>
    );
}
