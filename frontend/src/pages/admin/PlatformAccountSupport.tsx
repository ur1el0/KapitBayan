import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { AlertTriangle, KeyRound, LogOut, Search, ShieldCheck, UserRoundCog } from 'lucide-react';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { useAuth } from '../../context/auth-context';
import {
    correctPlatformAccountEmail,
    fetchPlatformAccounts,
    sendPlatformAccountRecoveryLink,
    setPlatformAccountActive,
    type AccountSupportReason,
    type PlatformAccount,
} from '../../api/platformAccountSupport';

const PAGE_SIZE = 50;
const REASONS: { value: AccountSupportReason; label: string }[] = [
    { value: 'INCORRECT_CONTACT', label: 'Incorrect contact details' },
    { value: 'LOCKED_OUT', label: 'Account holder is locked out' },
    { value: 'SECURITY_CONCERN', label: 'Security concern' },
    { value: 'STATUS_CORRECTION', label: 'Account status correction' },
    { value: 'OTHER_VERIFIED_SUPPORT', label: 'Other verified support issue' },
];

function apiErrorMessage(error: unknown, fallback: string) {
    if (!error || typeof error !== 'object' || !('response' in error)) return fallback;
    const response = error as { response?: { data?: Record<string, unknown> } };
    const data = response.response?.data;
    if (!data || typeof data !== 'object') return fallback;
    if (typeof data.detail === 'string') return data.detail;
    for (const key of ['email', 'contact_verified', 'reason', 'is_active']) {
        const value = data[key];
        if (typeof value === 'string') return value;
        if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
    }
    return fallback;
}

function barangayLabel(account: PlatformAccount) {
    if (account.barangay_id === null) return 'Unassigned account';
    const parts = [account.barangay_name, account.barangay_municipality, account.barangay_province]
        .filter((part): part is string => Boolean(part));
    return parts.join(', ') || `Barangay ID ${account.barangay_id}`;
}

function ReasonSelect({
    id,
    value,
    onChange,
}: {
    id: string;
    value: AccountSupportReason;
    onChange: (value: AccountSupportReason) => void;
}) {
    return (
        <div>
            <label htmlFor={id} className="block text-sm font-semibold text-slate-700">Support reason</label>
            <select
                id={id}
                value={value}
                onChange={(event) => onChange(event.target.value as AccountSupportReason)}
                className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:text-sm"
            >
                {REASONS.map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}
            </select>
        </div>
    );
}

export function PlatformAccountSupport() {
    const { logout } = useAuth();
    const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
    const [count, setCount] = useState(0);
    const [searchDraft, setSearchDraft] = useState('');
    const [search, setSearch] = useState('');
    const [role, setRole] = useState<PlatformAccount['role'] | ''>('');
    const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>('all');
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [retrying, setRetrying] = useState(false);
    const [loadError, setLoadError] = useState(false);
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [emailDraft, setEmailDraft] = useState('');
    const [emailReason, setEmailReason] = useState<AccountSupportReason>('INCORRECT_CONTACT');
    const [emailVerified, setEmailVerified] = useState(false);
    const [statusReason, setStatusReason] = useState<AccountSupportReason>('STATUS_CORRECTION');
    const [statusConfirmed, setStatusConfirmed] = useState(false);
    const [busyAction, setBusyAction] = useState<string | null>(null);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    const loadAccounts = useCallback(async (isRetry = false) => {
        if (isRetry) setRetrying(true);
        else setLoading(true);
        try {
            const result = await fetchPlatformAccounts({
                search,
                role,
                active: activeFilter === 'all' ? undefined : activeFilter === 'active',
                page,
            });
            setAccounts(Array.isArray(result.results) ? result.results : []);
            setCount(result.count);
            setLoadError(false);
        } catch {
            setLoadError(true);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    }, [activeFilter, page, role, search]);

    useEffect(() => { void loadAccounts(); }, [loadAccounts]);

    const submitSearch = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const normalized = searchDraft.trim();
        setMessage(null);
        if (normalized.length === 1) {
            setMessage({ type: 'error', text: 'Enter at least two characters, or clear the search to browse accounts.' });
            return;
        }
        setPage(1);
        setSearch(normalized);
    };

    const selectAccount = (account: PlatformAccount) => {
        setSelectedId((current) => current === account.id ? null : account.id);
        setEmailDraft(account.email);
        setEmailVerified(false);
        setStatusConfirmed(false);
        setMessage(null);
    };

    const updateAccount = (account: PlatformAccount) => {
        setAccounts((current) => current.map((item) => item.id === account.id ? account : item));
    };

    const submitEmailCorrection = async (event: FormEvent<HTMLFormElement>, account: PlatformAccount) => {
        event.preventDefault();
        if (!emailVerified) return;
        setBusyAction(`email-${account.id}`);
        setMessage(null);
        try {
            const updated = await correctPlatformAccountEmail(account.id, {
                email: emailDraft.trim().toLowerCase(),
                contact_verified: true,
                reason: emailReason,
            });
            updateAccount(updated);
            setMessage({ type: 'success', text: 'Email corrected. A private setup/reset link was requested for the updated address; email delivery may take a short time.' });
        } catch (error) {
            setMessage({ type: 'error', text: apiErrorMessage(error, 'Could not correct the account email.') });
        } finally {
            setBusyAction(null);
        }
    };

    const resendRecoveryLink = async (account: PlatformAccount) => {
        if (!emailVerified) return;
        setBusyAction(`link-${account.id}`);
        setMessage(null);
        try {
            await sendPlatformAccountRecoveryLink(account.id, {
                contact_verified: true,
                reason: emailReason,
            });
            setMessage({ type: 'success', text: 'A private setup/reset link was requested for the account email; email delivery may take a short time.' });
        } catch (error) {
            setMessage({ type: 'error', text: apiErrorMessage(error, 'Could not request a recovery link.') });
        } finally {
            setBusyAction(null);
        }
    };

    const changeActiveState = async (account: PlatformAccount) => {
        if (!statusConfirmed) return;
        setBusyAction(`status-${account.id}`);
        setMessage(null);
        try {
            const updated = await setPlatformAccountActive(account.id, {
                is_active: !account.is_active,
                reason: statusReason,
            });
            updateAccount(updated);
            setMessage({
                type: 'success',
                text: updated.is_active
                    ? 'Account reactivated. Previously revoked sessions remain signed out.'
                    : 'Account deactivated and active refresh sessions revoked.',
            });
            setStatusConfirmed(false);
        } catch (error) {
            setMessage({ type: 'error', text: apiErrorMessage(error, 'Could not update the account status.') });
        } finally {
            setBusyAction(null);
        }
    };

    const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));

    return (
        <main className="mx-auto max-w-7xl space-y-6 p-4 sm:p-8">
            <header className="flex flex-wrap items-start justify-between gap-4">
                <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-text">Platform operations</p>
                <h1 className="mt-1 flex items-center gap-3 text-2xl font-extrabold text-slate-900 sm:text-3xl">
                    <UserRoundCog className="h-7 w-7 text-primary-text" aria-hidden="true" />
                    Account support
                </h1>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                    Find barangay accounts, including legacy unassigned accounts, correct a verified contact address, send a private setup/reset link, or suspend access. These actions are audited.
                </p>
                </div>
                <button
                    type="button"
                    onClick={() => void logout()}
                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                    <LogOut className="h-4 w-4" aria-hidden="true" />
                    Log out
                </button>
            </header>

            <aside className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
                <p>Before changing an email or sending a recovery link, independently verify the account holder and their email through an official channel. Never ask for or enter passwords, one-time codes, or government ID details here.</p>
            </aside>

            {message && <p role={message.type === 'error' ? 'alert' : 'status'} className={`rounded-lg border p-3 text-sm ${message.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-900'}`}>{message.text}</p>}

            <form onSubmit={submitSearch} className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-[minmax(14rem,1fr)_12rem_12rem_auto] md:items-end">
                <div>
                    <label htmlFor="account-search" className="block text-sm font-semibold text-slate-700">Search accounts</label>
                    <div className="relative mt-1">
                        <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" aria-hidden="true" />
                        <input id="account-search" value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} maxLength={120} placeholder="Name, username, or email" className="min-h-11 w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:text-sm" />
                    </div>
                </div>
                <div>
                    <label htmlFor="account-role" className="block text-sm font-semibold text-slate-700">Role</label>
                    <select id="account-role" value={role} onChange={(event) => { setRole(event.target.value as PlatformAccount['role'] | ''); setPage(1); }} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:text-sm">
                        <option value="">All barangay roles</option>
                        <option value="RESIDENT">Resident</option>
                        <option value="FIELD_OFFICIAL">Field Official</option>
                        <option value="ADMIN">Barangay Administrator</option>
                    </select>
                </div>
                <div>
                    <label htmlFor="account-status" className="block text-sm font-semibold text-slate-700">Account status</label>
                    <select id="account-status" value={activeFilter} onChange={(event) => { setActiveFilter(event.target.value as typeof activeFilter); setPage(1); }} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:text-sm">
                        <option value="all">Active and inactive</option>
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                    </select>
                </div>
                <button type="submit" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                    <Search className="h-4 w-4" aria-hidden="true" /> Search
                </button>
            </form>

            {loading ? <p role="status" className="py-8 text-center text-sm text-slate-600">Loading accounts…</p> : loadError ? (
                <InlineErrorState message="We couldn't load account records." onRetry={() => { void loadAccounts(true); }} retrying={retrying} />
            ) : accounts.length === 0 ? (
                <div role="status" className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">No eligible barangay accounts match these filters.</div>
            ) : (
                <>
                    <section aria-label="Barangay accounts" className="space-y-3">
                        {accounts.map((account) => {
                            const expanded = selectedId === account.id;
                            return (
                                <article key={account.id} className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                                    <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
                                        <div className="min-w-0">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <h2 className="break-words text-base font-bold text-slate-900">{account.full_name}</h2>
                                                <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${account.is_active ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-100 text-slate-600'}`}>{account.is_active ? 'ACTIVE' : 'INACTIVE'}</span>
                                            </div>
                                            <p className="mt-1 break-all text-sm text-slate-700">{account.email || 'No email on file'} <span className="text-slate-400">· @{account.username}</span></p>
                                            <p className="mt-1 text-xs text-slate-600">{account.role.replaceAll('_', ' ')} · {barangayLabel(account)}</p>
                                        </div>
                                        <button type="button" aria-expanded={expanded} onClick={() => selectAccount(account)} className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                                            <ShieldCheck className="h-4 w-4" aria-hidden="true" /> {expanded ? 'Close support actions' : 'Manage account'}
                                        </button>
                                    </div>

                                    {expanded && (
                                        <div className="grid gap-6 border-t border-slate-200 bg-slate-50 p-4 sm:p-5 lg:grid-cols-2">
                                            <section aria-labelledby={`email-heading-${account.id}`} className="space-y-4">
                                                <div>
                                                    <h3 id={`email-heading-${account.id}`} className="font-bold text-slate-900">Contact and recovery</h3>
                                                    <p className="mt-1 text-xs leading-5 text-slate-600">Email correction sends a new private setup/reset link and revokes existing refresh sessions.</p>
                                                </div>
                                                <form onSubmit={(event) => void submitEmailCorrection(event, account)} className="space-y-3">
                                                    <div>
                                                        <label htmlFor={`email-${account.id}`} className="block text-sm font-semibold text-slate-700">Account email</label>
                                                        <input id={`email-${account.id}`} type="email" required maxLength={254} value={emailDraft} onChange={(event) => { setEmailDraft(event.target.value); setEmailVerified(false); }} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:text-sm" />
                                                    </div>
                                                    <ReasonSelect id={`email-reason-${account.id}`} value={emailReason} onChange={setEmailReason} />
                                                    <label className="flex items-start gap-3 text-sm leading-5 text-slate-700">
                                                        <input type="checkbox" checked={emailVerified} onChange={(event) => setEmailVerified(event.target.checked)} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus-visible:ring-2 focus-visible:ring-primary" />
                                                        <span>I independently verified the account holder and this email through an official channel.</span>
                                                    </label>
                                                    <button type="submit" disabled={!emailVerified || busyAction !== null} className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                                                        <KeyRound className="h-4 w-4" aria-hidden="true" /> {busyAction === `email-${account.id}` ? 'Saving…' : 'Save email and request setup link'}
                                                    </button>
                                                </form>
                                                <button type="button" disabled={!emailVerified || busyAction !== null || !account.email || emailDraft.trim().toLowerCase() !== account.email.toLowerCase()} onClick={() => void resendRecoveryLink(account)} className="min-h-11 w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                                                    {busyAction === `link-${account.id}` ? 'Requesting link…' : 'Resend setup/reset link to current email'}
                                                </button>
                                            </section>

                                            <section aria-labelledby={`status-heading-${account.id}`} className="space-y-4">
                                                <div>
                                                    <h3 id={`status-heading-${account.id}`} className="font-bold text-slate-900">Account access</h3>
                                                    <p className="mt-1 text-xs leading-5 text-slate-600">Deactivation blocks sign-in and revokes refresh sessions. Reactivation does not restore revoked sessions.</p>
                                                </div>
                                                <ReasonSelect id={`status-reason-${account.id}`} value={statusReason} onChange={setStatusReason} />
                                                <label className="flex items-start gap-3 text-sm leading-5 text-slate-700">
                                                    <input type="checkbox" checked={statusConfirmed} onChange={(event) => setStatusConfirmed(event.target.checked)} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus-visible:ring-2 focus-visible:ring-primary" />
                                                    <span>Confirm {account.is_active ? 'deactivation' : 'reactivation'} of this account.</span>
                                                </label>
                                                <button type="button" disabled={!statusConfirmed || busyAction !== null} onClick={() => void changeActiveState(account)} className={`min-h-11 w-full rounded-lg px-4 py-2 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${account.is_active ? 'border border-rose-300 bg-white text-rose-800 hover:bg-rose-50' : 'bg-emerald-700 text-white hover:bg-emerald-800'}`}>
                                                    {busyAction === `status-${account.id}` ? 'Updating…' : account.is_active ? 'Deactivate account' : 'Reactivate account'}
                                                </button>
                                                {account.role === 'ADMIN' && account.is_active && <p className="text-xs text-slate-600">The final active administrator for a barangay is protected from deactivation.</p>}
                                            </section>
                                        </div>
                                    )}
                                </article>
                            );
                        })}
                    </section>
                    <nav aria-label="Account result pages" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 text-sm">
                        <p className="text-slate-600">{count} eligible accounts · page {page} of {totalPages}</p>
                        <div className="flex gap-2">
                            <button type="button" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} className="min-h-11 rounded-lg border border-slate-300 px-4 font-semibold disabled:opacity-50">Previous</button>
                            <button type="button" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} className="min-h-11 rounded-lg border border-slate-300 px-4 font-semibold disabled:opacity-50">Next</button>
                        </div>
                    </nav>
                </>
            )}
        </main>
    );
}
