import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Bell, Building2, CalendarDays, CheckCircle2, Mail, Pencil, Phone, ShieldCheck, UserRound, X, type LucideIcon } from 'lucide-react';
import { axiosPrivate } from '../../api/axios';
import { useAuth } from '../../context/auth-context';
import type { User } from '../../context/auth-context';

interface ResidentAccount extends User {
    profile?: NonNullable<User['profile']> & {
        philsys_id_number?: string | null;
        secondary_id_type?: string | null;
        utility_billing_type?: string | null;
    };
}

interface ProfileDraft {
    full_name: string;
    contact_number: string;
    birth_date: string;
    voter_status: boolean;
}

function localDateString(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function toDraft(account: ResidentAccount): ProfileDraft {
    return {
        full_name: account.profile?.full_name ?? account.full_name ?? '',
        contact_number: account.profile?.contact_number ?? '',
        birth_date: account.profile?.birth_date ?? '',
        voter_status: account.profile?.voter_status ?? false,
    };
}

function InfoItem({ label, value, icon: Icon }: { label: string; value: string; icon: LucideIcon }) {
    return (
        <div className="flex min-w-0 items-start gap-3 rounded-xl bg-slate-50 p-4">
            <Icon className="mt-0.5 h-5 w-5 shrink-0 text-slate-500" aria-hidden="true" />
            <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-1 break-words text-sm font-semibold text-slate-900">{value || 'Not provided'}</p>
            </div>
        </div>
    );
}

export function ResidentProfileSettings() {
    const { updateUser } = useAuth();
    const [account, setAccount] = useState<ResidentAccount | null>(null);
    const [draft, setDraft] = useState<ProfileDraft>({
        full_name: '',
        contact_number: '',
        birth_date: '',
        voter_status: false,
    });
    const [isLoading, setIsLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [isSavingProfile, setIsSavingProfile] = useState(false);
    const [savingPreference, setSavingPreference] = useState<'email_alerts' | 'push_alerts' | null>(null);
    const [feedback, setFeedback] = useState<{ message: string; kind: 'success' | 'error' } | null>(null);

    const loadProfile = useCallback(async () => {
        setIsLoading(true);
        setLoadError(false);
        try {
            const response = await axiosPrivate.get('/auth/me/');
            const loadedAccount = response.data as ResidentAccount;
            setAccount(loadedAccount);
            setDraft(toDraft(loadedAccount));
            updateUser?.(loadedAccount);
        } catch {
            setLoadError(true);
        } finally {
            setIsLoading(false);
        }
    }, [updateUser]);

    useEffect(() => {
        void loadProfile();
    }, [loadProfile]);

    const handleSaveProfile = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!account) return;
        if (!draft.full_name.trim()) {
            setFeedback({ message: 'Enter your full name before saving.', kind: 'error' });
            return;
        }
        if (!draft.birth_date) {
            setFeedback({ message: 'Enter your birth date before saving.', kind: 'error' });
            return;
        }

        setIsSavingProfile(true);
        setFeedback(null);
        try {
            const response = await axiosPrivate.patch('/auth/me/', {
                profile: {
                    full_name: draft.full_name.trim(),
                    contact_number: draft.contact_number.trim(),
                    birth_date: draft.birth_date,
                    voter_status: draft.voter_status,
                },
            });
            const savedAccount = response.data as ResidentAccount;
            setAccount(savedAccount);
            setDraft(toDraft(savedAccount));
            updateUser?.(savedAccount);
            setIsEditing(false);
            setFeedback({ message: 'Your profile was updated.', kind: 'success' });
        } catch {
            setFeedback({ message: 'We could not save your profile. Check your details and try again.', kind: 'error' });
        } finally {
            setIsSavingProfile(false);
        }
    };

    const handlePreferenceChange = async (field: 'email_alerts' | 'push_alerts', enabled: boolean) => {
        setSavingPreference(field);
        setFeedback(null);
        try {
            const response = await axiosPrivate.patch('/auth/me/', { [field]: enabled });
            const savedAccount = response.data as ResidentAccount;
            setAccount((current) => current ? { ...current, ...savedAccount } : savedAccount);
            updateUser?.(savedAccount);
            setFeedback({ message: 'Notification preference saved.', kind: 'success' });
        } catch {
            setFeedback({ message: 'We could not save that preference. Please try again.', kind: 'error' });
        } finally {
            setSavingPreference(null);
        }
    };

    const cancelEditing = () => {
        if (account) setDraft(toDraft(account));
        setIsEditing(false);
        setFeedback(null);
    };

    if (isLoading) {
        return (
            <div aria-busy="true" className="mx-auto max-w-4xl py-8">
                <p className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading your profile and settings…</p>
            </div>
        );
    }

    if (loadError || !account) {
        return (
            <div className="mx-auto max-w-4xl py-8">
                <section className="rounded-2xl border border-rose-200 bg-white p-6" aria-labelledby="profile-load-error" role="alert">
                    <h1 id="profile-load-error" className="text-xl font-bold text-slate-900">Profile unavailable</h1>
                    <p className="mt-2 text-sm text-slate-600">We could not load your account details. Check your connection and try again.</p>
                    <button type="button" onClick={() => void loadProfile()} className="mt-4 min-h-11 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                        Try again
                    </button>
                </section>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-4xl space-y-6 pb-8">
            <header className="flex flex-wrap items-end justify-between gap-4">
                <div>
                    <p className="text-sm font-bold uppercase tracking-[0.14em] text-primary-text">Resident account</p>
                    <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-900">My Profile &amp; Settings</h1>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Review your resident details and choose how KapitBayan sends service updates.</p>
                </div>
                {!isEditing && (
                    <button type="button" onClick={() => { setDraft(toDraft(account)); setIsEditing(true); setFeedback(null); }} className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-bold text-primary-foreground shadow-sm hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                        Edit profile
                    </button>
                )}
            </header>

            {feedback && (
                <p role={feedback.kind === 'error' ? 'alert' : 'status'} aria-live={feedback.kind === 'error' ? 'assertive' : 'polite'} className={`rounded-xl border px-4 py-3 text-sm font-medium ${feedback.kind === 'error' ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800'}`}>
                    {feedback.message}
                </p>
            )}

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-labelledby="resident-details-heading">
                <div className="flex items-center gap-3 border-b border-slate-100 p-5 sm:p-6">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-primary-text"><UserRound className="h-5 w-5" aria-hidden="true" /></span>
                    <div>
                        <h2 id="resident-details-heading" className="text-lg font-bold text-slate-900">Resident details</h2>
                        <p className="text-sm text-slate-600">Your username and email are shown for reference. Edit the resident information below.</p>
                    </div>
                </div>
                <div className="p-5 sm:p-6">
                    {isEditing ? (
                        <form onSubmit={(event) => void handleSaveProfile(event)} className="space-y-5">
                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                <label className="block text-sm font-semibold text-slate-800 sm:col-span-2" htmlFor="resident-full-name">
                                    Full name
                                    <input id="resident-full-name" name="full_name" autoComplete="name" required maxLength={255} value={draft.full_name} onChange={(event) => setDraft((current) => ({ ...current, full_name: event.target.value }))} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
                                </label>
                                <label className="block text-sm font-semibold text-slate-800" htmlFor="resident-contact-number">
                                    Contact number
                                    <input id="resident-contact-number" name="contact_number" type="tel" autoComplete="tel" maxLength={20} value={draft.contact_number} onChange={(event) => setDraft((current) => ({ ...current, contact_number: event.target.value }))} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
                                </label>
                                <label className="block text-sm font-semibold text-slate-800" htmlFor="resident-birth-date">
                                    Birth date
                                    <input id="resident-birth-date" name="birth_date" type="date" autoComplete="bday" min="1900-01-01" max={localDateString(new Date())} value={draft.birth_date} onChange={(event) => setDraft((current) => ({ ...current, birth_date: event.target.value }))} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
                                </label>
                                <label className="flex min-h-12 items-center gap-3 rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-800 sm:col-span-2">
                                    <input type="checkbox" name="voter_status" checked={draft.voter_status} onChange={(event) => setDraft((current) => ({ ...current, voter_status: event.target.checked }))} className="h-5 w-5 rounded accent-primary" />
                                    I am a registered voter in this barangay
                                </label>
                            </div>
                            <div className="flex flex-wrap gap-3">
                                <button type="submit" disabled={isSavingProfile} className="min-h-11 rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                                    {isSavingProfile ? 'Saving…' : 'Save changes'}
                                </button>
                                <button type="button" onClick={cancelEditing} disabled={isSavingProfile} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 px-5 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                                    <X className="h-4 w-4" aria-hidden="true" /> Cancel
                                </button>
                            </div>
                        </form>
                    ) : (
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                            <InfoItem label="Full name" value={account.profile?.full_name ?? account.full_name ?? ''} icon={UserRound} />
                            <InfoItem label="Contact number" value={account.profile?.contact_number ?? ''} icon={Phone} />
                            <InfoItem label="Birth date" value={account.profile?.birth_date ?? ''} icon={CalendarDays} />
                            <InfoItem label="Voter status" value={account.profile?.voter_status ? 'Registered voter' : 'Not registered'} icon={CheckCircle2} />
                            <InfoItem label="Username" value={account.username ?? ''} icon={UserRound} />
                            <InfoItem label="Email address" value={account.email ?? ''} icon={Mail} />
                            <InfoItem label="Barangay" value={account.barangay?.name ?? ''} icon={Building2} />
                            <InfoItem label="Verification" value={account.profile?.is_verified ? 'Verified resident' : 'Pending verification'} icon={ShieldCheck} />
                        </div>
                    )}
                </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-labelledby="resident-notifications-heading">
                <div className="flex items-center gap-3 border-b border-slate-100 p-5 sm:p-6">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-700"><Bell className="h-5 w-5" aria-hidden="true" /></span>
                    <div>
                        <h2 id="resident-notifications-heading" className="text-lg font-bold text-slate-900">Notification preferences</h2>
                        <p className="text-sm text-slate-600">Choose where you want to receive service updates.</p>
                    </div>
                </div>
                <div className="divide-y divide-slate-100 px-5 sm:px-6">
                    <label className="flex min-h-[76px] cursor-pointer items-center justify-between gap-4 py-4">
                        <span className="min-w-0">
                            <span className="block font-semibold text-slate-900">Email updates</span>
                            <span className="mt-1 block text-sm leading-5 text-slate-600">Updates about your service requests sent to {account.email || 'your account email'}.</span>
                        </span>
                        <input type="checkbox" role="switch" aria-label="Email updates" checked={account.email_alerts ?? true} disabled={savingPreference !== null || !account.email} onChange={(event) => void handlePreferenceChange('email_alerts', event.target.checked)} className="h-5 w-5 shrink-0 accent-primary disabled:opacity-50" />
                    </label>
                    <label className="flex min-h-[76px] cursor-pointer items-center justify-between gap-4 py-4">
                        <span className="min-w-0">
                            <span className="block font-semibold text-slate-900">Push notifications</span>
                            <span className="mt-1 block text-sm leading-5 text-slate-600">Queue calls and service alerts on mobile devices registered to your account. Allow notifications in Android and the KapitBayan app.</span>
                        </span>
                        <input type="checkbox" role="switch" aria-label="Push notifications for registered mobile devices" checked={account.push_alerts ?? false} disabled={savingPreference !== null} onChange={(event) => void handlePreferenceChange('push_alerts', event.target.checked)} className="h-5 w-5 shrink-0 accent-primary disabled:opacity-50" />
                    </label>
                </div>
            </section>
        </div>
    );
}
