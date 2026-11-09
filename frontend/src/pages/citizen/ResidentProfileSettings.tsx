import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { ArrowRightLeft, Bell, Building2, CalendarDays, CheckCircle2, Mail, Pencil, Phone, ShieldCheck, UserRound, X, type LucideIcon } from 'lucide-react';
import { axiosPrivate } from '../../api/axios';
import { useAuth } from '../../context/auth-context';
import type { User } from '../../context/auth-context';
import { useLanguage } from '../../context/language-context';
import { LanguageSwitcher } from '../../components/language/LanguageSwitcher';

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

interface TransferBarangayOption {
    id: number;
    name: string;
    municipality?: string;
    province?: string;
}

interface TransferRequest {
    id: number;
    source_barangay_name: string;
    destination_barangay_name: string;
    purok?: string;
    address_details?: string;
    has_proof_of_residency?: boolean;
    reason: string;
    status: string;
    review_note: string;
    created_at: string;
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
    const { t } = useLanguage();
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
    const [transferOptions, setTransferOptions] = useState<TransferBarangayOption[]>([]);
    const [transferRequests, setTransferRequests] = useState<TransferRequest[]>([]);
    const [transferDestinationId, setTransferDestinationId] = useState('');
    const [transferReason, setTransferReason] = useState('');
    const [transferPurok, setTransferPurok] = useState('');
    const [transferAddressDetails, setTransferAddressDetails] = useState('');
    const [transferProofFile, setTransferProofFile] = useState<File | null>(null);
    const [transferProofError, setTransferProofError] = useState<string | null>(null);
    const [transferLoading, setTransferLoading] = useState(true);
    const [transferLoadError, setTransferLoadError] = useState(false);
    const [transferSubmitting, setTransferSubmitting] = useState(false);
    const [transferFeedback, setTransferFeedback] = useState<{ message: string; kind: 'success' | 'error' } | null>(null);

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

    const loadTransfers = useCallback(async () => {
        setTransferLoading(true);
        setTransferLoadError(false);
        try {
            const [barangayResponse, requestResponse] = await Promise.all([
                axiosPrivate.get('/auth/public/barangays/'),
                axiosPrivate.get('/auth/resident-transfers/'),
            ]);
            const barangayRows = Array.isArray(barangayResponse.data)
                ? barangayResponse.data
                : barangayResponse.data?.results;
            const requestRows = Array.isArray(requestResponse.data)
                ? requestResponse.data
                : requestResponse.data?.results;
            if (!Array.isArray(barangayRows) || !Array.isArray(requestRows)) {
                throw new Error('Invalid transfer directory response.');
            }
            setTransferOptions(barangayRows as TransferBarangayOption[]);
            setTransferRequests(requestRows as TransferRequest[]);
        } catch {
            setTransferLoadError(true);
        } finally {
            setTransferLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadProfile();
    }, [loadProfile]);

    useEffect(() => {
        void loadTransfers();
    }, [loadTransfers]);

    const handleProofFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0] || null;
        if (!file) {
            setTransferProofFile(null);
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            setTransferProofError(t('Residency proof image must be 5 MiB or smaller.'));
            setTransferProofFile(null);
            e.target.value = '';
            return;
        }
        setTransferProofError(null);
        setTransferProofFile(file);
    };

    const handleTransferSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!transferDestinationId || !transferReason.trim()) {
            setTransferFeedback({ message: t('Choose a Barangay and explain why you are moving.'), kind: 'error' });
            return;
        }
        if (!transferProofFile) {
            setTransferProofError(t('Upload proof of residency to request a transfer.'));
            return;
        }

        setTransferSubmitting(true);
        setTransferFeedback(null);
        setTransferProofError(null);
        try {
            const formData = new FormData();
            formData.append('destination_barangay_id', transferDestinationId);
            formData.append('reason', transferReason.trim());
            if (transferPurok.trim()) {
                formData.append('purok', transferPurok.trim());
            }
            if (transferAddressDetails.trim()) {
                formData.append('address_details', transferAddressDetails.trim());
            }
            formData.append('proof_of_residency', transferProofFile);

            await axiosPrivate.post('/auth/resident-transfers/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setTransferReason('');
            setTransferDestinationId('');
            setTransferPurok('');
            setTransferAddressDetails('');
            setTransferProofFile(null);
            setTransferFeedback({ message: t('Transfer request sent to the receiving Barangay for verification.'), kind: 'success' });
            await loadTransfers();
        } catch (error: unknown) {
            const apiError = error as { response?: { data?: { detail?: string; proof_of_residency?: string[]; destination_barangay_id?: string[] } } };
            const detail = apiError?.response?.data?.detail
                || apiError?.response?.data?.proof_of_residency?.[0]
                || apiError?.response?.data?.destination_barangay_id?.[0]
                || t('We could not submit your transfer request. Check the details and try again.');
            setTransferFeedback({ message: String(detail), kind: 'error' });
        } finally {
            setTransferSubmitting(false);
        }
    };

    const handleSaveProfile = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!account) return;
        if (!draft.full_name.trim()) {
            setFeedback({ message: t('Enter your full name before saving.'), kind: 'error' });
            return;
        }
        if (!draft.birth_date) {
            setFeedback({ message: t('Enter your birth date before saving.'), kind: 'error' });
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
            setFeedback({ message: t('Your profile was updated.'), kind: 'success' });
        } catch {
            setFeedback({ message: t('We could not save your profile. Check your details and try again.'), kind: 'error' });
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
            setFeedback({ message: t('Notification preference saved.'), kind: 'success' });
        } catch {
            setFeedback({ message: t('Could not save that preference. Please try again.'), kind: 'error' });
        } finally {
            setSavingPreference(null);
        }
    };

    const currentBarangayId = account?.barangay_id ?? account?.barangay?.id;
    const availableTransferOptions = transferOptions.filter(
        (barangay) => String(barangay.id) !== String(currentBarangayId ?? ''),
    );
    const hasPendingTransfer = transferRequests.some((request) => request.status === 'PENDING');

    const cancelEditing = () => {
        if (account) setDraft(toDraft(account));
        setIsEditing(false);
        setFeedback(null);
    };

    if (isLoading) {
        return (
            <div aria-busy="true" className="mx-auto max-w-4xl py-8">
                <p className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600">{t('Loading your profile and settings…')}</p>
            </div>
        );
    }

    if (loadError || !account) {
        return (
            <div className="mx-auto max-w-4xl py-8">
                <section className="rounded-2xl border border-rose-200 bg-white p-6" aria-labelledby="profile-load-error" role="alert">
                    <h1 id="profile-load-error" className="text-xl font-bold text-slate-900">{t('Profile unavailable')}</h1>
                    <p className="mt-2 text-sm text-slate-600">{t('We could not load your account details. Check your connection and try again.')}</p>
                    <button type="button" onClick={() => void loadProfile()} className="mt-4 min-h-11 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                        {t('Try again')}
                    </button>
                </section>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-4xl space-y-6 pb-8">
            <header className="flex flex-wrap items-end justify-between gap-4">
                <div>
                    <p className="text-sm font-bold uppercase tracking-[0.14em] text-primary-text">{t('Resident account')}</p>
                    <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-900">{t('My Profile & Settings')}</h1>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{t('Review your resident details and manage service update emails.')}</p>
                </div>
                {!isEditing && (
                    <button type="button" onClick={() => { setDraft(toDraft(account)); setIsEditing(true); setFeedback(null); }} className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-bold text-primary-foreground shadow-sm hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                        {t('Edit profile')}
                    </button>
                )}
            </header>

            <section className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="resident-language-heading">
                <div>
                    <h2 id="resident-language-heading" className="font-bold text-slate-900">{t('Language')}</h2>
                    <p className="mt-1 text-sm text-slate-600">{t('Choose the language you prefer to use.')}</p>
                </div>
                <LanguageSwitcher />
            </section>

            {feedback && (
                <p role={feedback.kind === 'error' ? 'alert' : 'status'} aria-live={feedback.kind === 'error' ? 'assertive' : 'polite'} className={`rounded-xl border px-4 py-3 text-sm font-medium ${feedback.kind === 'error' ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800'}`}>
                    {feedback.message}
                </p>
            )}

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-labelledby="resident-details-heading">
                <div className="flex items-center gap-3 border-b border-slate-100 p-5 sm:p-6">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-primary-text"><UserRound className="h-5 w-5" aria-hidden="true" /></span>
                    <div>
                        <h2 id="resident-details-heading" className="text-lg font-bold text-slate-900">{t('Resident details')}</h2>
                        <p className="text-sm text-slate-600">{t('Your username and email are shown for reference. Edit the resident information below.')}</p>
                    </div>
                </div>
                <div className="p-5 sm:p-6">
                    {isEditing ? (
                        <form onSubmit={(event) => void handleSaveProfile(event)} className="space-y-5">
                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                <label className="block text-sm font-semibold text-slate-800 sm:col-span-2" htmlFor="resident-full-name">
                                    {t('Full name')}
                                    <input id="resident-full-name" name="full_name" autoComplete="name" required maxLength={255} value={draft.full_name} onChange={(event) => setDraft((current) => ({ ...current, full_name: event.target.value }))} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
                                </label>
                                <label className="block text-sm font-semibold text-slate-800" htmlFor="resident-contact-number">
                                    {t('Contact number')}
                                    <input id="resident-contact-number" name="contact_number" type="tel" autoComplete="tel" maxLength={20} value={draft.contact_number} onChange={(event) => setDraft((current) => ({ ...current, contact_number: event.target.value }))} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
                                </label>
                                <label className="block text-sm font-semibold text-slate-800" htmlFor="resident-birth-date">
                                    {t('Birth date')}
                                    <input id="resident-birth-date" name="birth_date" type="date" autoComplete="bday" min="1900-01-01" max={localDateString(new Date())} value={draft.birth_date} onChange={(event) => setDraft((current) => ({ ...current, birth_date: event.target.value }))} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
                                </label>
                                <label className="flex min-h-12 items-center gap-3 rounded-xl border border-slate-200 px-4 text-sm font-semibold text-slate-800 sm:col-span-2">
                                    <input type="checkbox" name="voter_status" checked={draft.voter_status} onChange={(event) => setDraft((current) => ({ ...current, voter_status: event.target.checked }))} className="h-5 w-5 rounded accent-primary" />
                                    {t('I am a registered voter in this barangay')}
                                </label>
                            </div>
                            <div className="flex flex-wrap gap-3">
                                <button type="submit" disabled={isSavingProfile} className="min-h-11 rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                                    {isSavingProfile ? t('Saving…') : t('Save changes')}
                                </button>
                                <button type="button" onClick={cancelEditing} disabled={isSavingProfile} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 px-5 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                                    <X className="h-4 w-4" aria-hidden="true" /> {t('Cancel')}
                                </button>
                            </div>
                        </form>
                    ) : (
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                            <InfoItem label={t('Full name')} value={account.profile?.full_name ?? account.full_name ?? ''} icon={UserRound} />
                            <InfoItem label={t('Contact number')} value={account.profile?.contact_number ?? ''} icon={Phone} />
                            <InfoItem label={t('Birth date')} value={account.profile?.birth_date ?? ''} icon={CalendarDays} />
                            <InfoItem label={t('Voter status')} value={account.profile?.voter_status ? t('Registered voter') : t('Not registered')} icon={CheckCircle2} />
                            <InfoItem label={t('Username')} value={account.username ?? ''} icon={UserRound} />
                            <InfoItem label={t('Email address')} value={account.email ?? ''} icon={Mail} />
                            <InfoItem label={t('Barangay')} value={account.barangay?.name ?? ''} icon={Building2} />
                            <InfoItem label={t('Verification')} value={account.profile?.is_verified ? t('Verified resident') : t('Pending verification')} icon={ShieldCheck} />
                        </div>
                    )}
                </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-labelledby="barangay-transfer-heading">
                <div className="flex items-center gap-3 border-b border-slate-100 p-5 sm:p-6">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700"><ArrowRightLeft className="h-5 w-5" aria-hidden="true" /></span>
                    <div>
                        <h2 id="barangay-transfer-heading" className="text-lg font-bold text-slate-900">{t('Move to another Barangay')}</h2>
                        <p className="text-sm text-slate-600">{t('Request an account transfer if you have moved. The receiving Barangay must verify your identity and residence before the account is moved.')}</p>
                    </div>
                </div>
                <div className="space-y-5 p-5 sm:p-6">
                    {transferFeedback && (
                        <p role={transferFeedback.kind === 'error' ? 'alert' : 'status'} aria-live={transferFeedback.kind === 'error' ? 'assertive' : 'polite'} className={`rounded-xl border px-4 py-3 text-sm font-medium ${transferFeedback.kind === 'error' ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800'}`}>
                            {transferFeedback.message}
                        </p>
                    )}
                    {transferLoadError ? (
                        <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
                            <p>{t('We could not load the Barangay transfer information.')}</p>
                            <button type="button" onClick={() => void loadTransfers()} className="mt-3 min-h-11 rounded-lg border border-rose-300 bg-white px-4 font-semibold">{t('Try again')}</button>
                        </div>
                    ) : transferLoading ? (
                        <p role="status" className="text-sm text-slate-500">{t('Loading transfer information…')}</p>
                    ) : !account.profile?.is_verified ? (
                        <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{t('Barangay transfer requests are available after your resident account is verified.')}</p>
                    ) : hasPendingTransfer ? (
                        <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{t('You already have a transfer request waiting for review. You can submit another after it is approved or rejected.')}</p>
                    ) : (
                        <form onSubmit={(event) => void handleTransferSubmit(event)} className="space-y-4">
                            <label htmlFor="transfer-destination" className="block text-sm font-semibold text-slate-800">
                                {t('Receiving Barangay')}
                                <select id="transfer-destination" required value={transferDestinationId} onChange={(event) => setTransferDestinationId(event.target.value)} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20">
                                    <option value="">{t('Choose a Barangay')}</option>
                                    {availableTransferOptions.map((barangay) => (
                                        <option key={barangay.id} value={barangay.id}>
                                            {[barangay.name, barangay.municipality, barangay.province].filter(Boolean).join(', ')}
                                        </option>
                                    ))}
                                </select>
                            </label>

                            <div className="grid gap-4 sm:grid-cols-2">
                                <label htmlFor="transfer-purok" className="block text-sm font-semibold text-slate-800">
                                    {t('Purok / Zone')} <span className="text-xs font-normal text-slate-500">({t('if applicable')})</span>
                                    <input
                                        id="transfer-purok"
                                        type="text"
                                        maxLength={100}
                                        value={transferPurok}
                                        onChange={(event) => setTransferPurok(event.target.value)}
                                        placeholder={t('e.g. Purok 3')}
                                        className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                                    />
                                </label>

                                <label htmlFor="transfer-address" className="block text-sm font-semibold text-slate-800">
                                    {t('New Street Address / Details')}
                                    <input
                                        id="transfer-address"
                                        type="text"
                                        maxLength={255}
                                        value={transferAddressDetails}
                                        onChange={(event) => setTransferAddressDetails(event.target.value)}
                                        placeholder={t('e.g. 123 Rizal Street')}
                                        className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                                    />
                                </label>
                            </div>

                            <div>
                                <label htmlFor="transfer-proof" className="block text-sm font-semibold text-slate-800">
                                    {t('Proof of Residency')} <span className="text-xs font-normal text-slate-500">({t('utility bill, lease, or certificate')})</span>
                                    <input
                                        id="transfer-proof"
                                        type="file"
                                        accept="image/*"
                                        required
                                        onChange={handleProofFileChange}
                                        className="mt-2 block w-full text-sm text-slate-600 file:mr-4 file:min-h-11 file:rounded-xl file:border-0 file:bg-primary/10 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-primary hover:file:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                                    />
                                </label>
                                {transferProofError && (
                                    <p role="alert" className="mt-1 text-xs font-semibold text-rose-700">{transferProofError}</p>
                                )}
                                <p className="mt-1 text-xs text-slate-500">{t('Image file up to 5 MiB.')}</p>
                            </div>

                            <label htmlFor="transfer-reason" className="block text-sm font-semibold text-slate-800">
                                {t('Reason for moving')}
                                <textarea id="transfer-reason" required maxLength={500} value={transferReason} onChange={(event) => setTransferReason(event.target.value)} rows={3} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-base font-normal text-slate-900 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20" />
                            </label>
                            {availableTransferOptions.length === 0 && (
                                <p className="text-sm text-slate-600">{t('No other approved Barangays are currently available for transfer.')}</p>
                            )}
                            <p className="text-xs leading-5 text-slate-500">{t('Your Barangay assignment changes only after approval. Existing requests and queue records stay with the Barangay that handled them.')}</p>
                            <button type="submit" disabled={transferSubmitting || availableTransferOptions.length === 0} className="min-h-11 rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2">
                                {transferSubmitting ? t('Submitting…') : t('Submit transfer request')}
                            </button>
                        </form>
                    )}

                    {transferRequests.length > 0 && (
                        <div className="space-y-3 border-t border-slate-100 pt-5">
                            <h3 className="font-bold text-slate-900">{t('Transfer request history')}</h3>
                            {transferRequests.map((request) => (
                                <article key={request.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <p className="text-sm font-semibold text-slate-800">{request.source_barangay_name} → {request.destination_barangay_name}</p>
                                        <span className={`rounded-full px-3 py-1 text-xs font-bold ${request.status === 'PENDING' ? 'bg-amber-100 text-amber-900' : request.status === 'APPROVED' ? 'bg-emerald-100 text-emerald-900' : 'bg-rose-100 text-rose-900'}`}>
                                            {t(request.status)}
                                        </span>
                                    </div>
                                    {(request.purok || request.address_details) && (
                                        <p className="mt-1 text-xs text-slate-600">
                                            <strong>{t('New residence')}:</strong> {[request.purok, request.address_details].filter(Boolean).join(', ')}
                                        </p>
                                    )}
                                    <p className="mt-2 text-sm text-slate-600">{request.reason}</p>
                                    {request.status === 'REJECTED' && request.review_note && (
                                        <div role="alert" className="mt-2 rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-900">
                                            <strong>{t('Rejection reason')}:</strong> {request.review_note}
                                        </div>
                                    )}
                                    {request.status === 'APPROVED' && request.review_note && (
                                        <p className="mt-2 text-xs text-slate-600"><strong>{t('Admin note')}:</strong> {request.review_note}</p>
                                    )}
                                    <p className="mt-2 text-xs text-slate-500">{new Date(request.created_at).toLocaleString()}</p>
                                </article>
                            ))}
                        </div>
                    )}
                </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-labelledby="resident-notifications-heading">
                <div className="flex items-center gap-3 border-b border-slate-100 p-5 sm:p-6">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-700"><Bell className="h-5 w-5" aria-hidden="true" /></span>
                    <div>
                        <h2 id="resident-notifications-heading" className="text-lg font-bold text-slate-900">{t('Email preferences')}</h2>
                        <p className="text-sm text-slate-600">{t('Manage the service update emails sent to your account.')}</p>
                    </div>
                </div>
                <div className="divide-y divide-slate-100 px-5 sm:px-6">
                    <label className="flex min-h-[76px] cursor-pointer items-center justify-between gap-4 py-4">
                        <span className="min-w-0">
                            <span className="block font-semibold text-slate-900">{t('Email updates')}</span>
                            <span className="mt-1 block text-sm leading-5 text-slate-600">{t('Updates about your service requests sent to')} {account.email || t('your account email')}.</span>
                        </span>
                        <input type="checkbox" role="switch" aria-label="Email updates" checked={account.email_alerts ?? true} disabled={savingPreference !== null || !account.email} onChange={(event) => void handlePreferenceChange('email_alerts', event.target.checked)} className="h-5 w-5 shrink-0 accent-primary disabled:opacity-50" />
                    </label>
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                        <p className="font-semibold text-slate-900">{t('Mobile push alerts')}</p>
                        <p className="mt-1 text-sm leading-5 text-slate-600">{t('Push preferences are managed in the KapitBayan mobile app. This web page does not register a phone for push alerts.')}</p>
                    </div>
                </div>
            </section>
        </div>
    );
}
