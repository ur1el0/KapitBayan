import React, { useEffect, useRef, useState } from 'react';
import { Building2, Camera, Mail, ShieldCheck, UserRound } from 'lucide-react';
import { axiosPrivate } from '../../api/axios';
import { useAuth } from '../../context/auth-context';
import { getMediaUrl } from '../../utils/media-url';

const MAX_PROFILE_PICTURE_BYTES = 5 * 1024 * 1024;

export const AdminProfile: React.FC = () => {
    const { user, updateUser } = useAuth();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [profilePicture, setProfilePicture] = useState<string | null>(user?.profile_picture ?? null);
    const [selectedPicture, setSelectedPicture] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [isSavingPicture, setIsSavingPicture] = useState(false);
    const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

    useEffect(() => {
        let isCurrent = true;
        axiosPrivate.get('/auth/me/').then(({ data }) => {
            if (!isCurrent) return;
            setProfilePicture(data.profile_picture ?? null);
            updateUser?.(data);
        }).catch(() => {
            // Keep the authenticated profile data available if this refresh fails.
        });
        return () => { isCurrent = false; };
    }, [updateUser]);

    useEffect(() => {
        if (!selectedPicture) {
            setPreviewUrl(null);
            return;
        }
        const objectUrl = URL.createObjectURL(selectedPicture);
        setPreviewUrl(objectUrl);
        return () => URL.revokeObjectURL(objectUrl);
    }, [selectedPicture]);

    if (!user) return null;

    const fullName = user.full_name?.trim() || user.username || 'Barangay Official';
    const initial = fullName.charAt(0).toUpperCase();
    const roleLabel = user.role === 'DILG_ADMIN'
        ? 'DILG Administrator'
        : user.is_superuser
            ? 'Platform Administrator'
            : 'Barangay Administrator';

    const savePicture = async (picture: File | null = selectedPicture) => {
        if (!picture) return;
        setIsSavingPicture(true);
        setFeedback(null);
        const formData = new FormData();
        formData.append('profile_picture', picture);
        try {
            const { data } = await axiosPrivate.patch('/auth/me/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setProfilePicture(data.profile_picture ?? null);
            updateUser?.(data);
            setSelectedPicture(null);
            setFeedback({ type: 'success', message: 'Profile picture updated.' });
        } catch (requestError: any) {
            setFeedback({
                type: 'error',
                message: requestError.response?.data?.profile_picture?.[0]
                    || requestError.response?.data?.detail
                    || 'Could not save your profile picture. Please try again.',
            });
        } finally {
            setIsSavingPicture(false);
        }
    };

    const handlePictureSelected = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        event.target.value = '';
        if (!file) return;
        if (!file.type.startsWith('image/')) {
            setFeedback({ type: 'error', message: 'Choose an image file for your profile picture.' });
            return;
        }
        if (file.size > MAX_PROFILE_PICTURE_BYTES) {
            setFeedback({ type: 'error', message: 'Choose an image that is 5 MB or smaller.' });
            return;
        }
        setFeedback(null);
        setSelectedPicture(file);
        void savePicture(file);
    };

    const displayedPicture = previewUrl || getMediaUrl(profilePicture, axiosPrivate.defaults.baseURL);

    return (
        <div className="mx-auto w-full max-w-5xl space-y-6 pb-4">
            <header>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#547095]">Account settings</p>
                <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-[#091B35] sm:text-3xl">Admin Profile</h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">View and update the identity connected to your KapitBayan administration account.</p>
            </header>

            <section aria-label="Administrator profile" className="overflow-hidden rounded-2xl border border-[#DCE5F0] bg-white shadow-sm">
                <div className="relative h-36 overflow-hidden bg-gradient-to-r from-[#091B35] via-[#0F2D59] to-[#174B83] sm:h-44">
                    <div aria-hidden="true" className="absolute -right-12 -top-28 h-72 w-72 rounded-full border border-white/10" />
                    <div aria-hidden="true" className="absolute -right-2 -top-20 h-60 w-60 rounded-full border border-white/10" />
                    <div aria-hidden="true" className="absolute bottom-0 left-0 h-1 w-full bg-gradient-to-r from-sky-400 via-cyan-300 to-amber-300" />
                </div>

                <div className="px-5 pb-6 sm:px-8 sm:pb-8">
                    <div className="relative -mt-12 flex flex-col gap-4 sm:-mt-14 sm:flex-row sm:items-end sm:justify-between">
                        <div className="flex min-w-0 flex-col items-start gap-3">
                            <div className="relative h-24 w-24 shrink-0 rounded-2xl border-4 border-white bg-[#EAF1FA] shadow-md sm:h-28 sm:w-28">
                                {displayedPicture ? (
                                    <img src={displayedPicture} alt={`${fullName} profile picture`} className="h-full w-full rounded-[0.8rem] object-cover" />
                                ) : (
                                    <div aria-label={`${fullName} profile initial`} className="flex h-full w-full items-center justify-center rounded-[0.8rem] text-4xl font-extrabold text-[#0F2D59] sm:text-5xl">{initial}</div>
                                )}
                                <button type="button" onClick={() => fileInputRef.current?.click()} disabled={isSavingPicture} aria-label={profilePicture ? 'Change profile picture' : 'Add profile picture'} className="absolute -bottom-2 -right-2 inline-flex h-9 w-9 items-center justify-center rounded-xl border-2 border-white bg-[#0F2D59] text-white shadow-md transition-colors hover:bg-[#174B83] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 disabled:opacity-60">
                                    <Camera className="h-4 w-4" aria-hidden="true" />
                                </button>
                                <input ref={fileInputRef} type="file" accept="image/*" className="sr-only" aria-label="Profile picture file" onChange={handlePictureSelected} />
                            </div>
                            <div className="min-w-0">
                                <h2 className="break-words text-xl font-extrabold tracking-tight text-[#091B35] sm:text-2xl">{fullName}</h2>
                                <p className="mt-1 text-sm font-medium text-slate-500">{roleLabel}</p>
                            </div>
                        </div>
                        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-[#C9D8EA] bg-[#F1F6FC] px-3.5 py-2 text-xs font-bold text-[#153D6B]">
                            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                            Administrator Access
                        </span>
                    </div>

                    {isSavingPicture && <p role="status" className="mt-4 text-sm font-medium text-slate-500">Saving profile picture…</p>}
                    {feedback && <p role={feedback.type === 'error' ? 'alert' : 'status'} className={`mt-4 text-sm font-medium ${feedback.type === 'error' ? 'text-rose-700' : 'text-emerald-700'}`}>{feedback.message}</p>}

                    <div className="mt-7 grid gap-4 border-t border-slate-100 pt-6 sm:grid-cols-2">
                        <div className="rounded-xl border border-slate-200 bg-[#FBFCFE] p-4 sm:p-5">
                            <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-[0.12em] text-[#647B98]"><Mail className="h-4 w-4 text-[#315B8A]" aria-hidden="true" />Contact information</div>
                            <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">Sign-in email</p>
                            <p className="mt-1 break-all text-sm font-semibold text-slate-800">{user.email || 'No email provided'}</p>
                        </div>
                        <div className="rounded-xl border border-slate-200 bg-[#FBFCFE] p-4 sm:p-5">
                            <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-[0.12em] text-[#647B98]"><Building2 className="h-4 w-4 text-[#315B8A]" aria-hidden="true" />Barangay access</div>
                            <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">Assigned barangay</p>
                            <p className="mt-1 text-sm font-semibold text-slate-800">{user.barangay?.name || 'Platform-wide access'}</p>
                        </div>
                        <div className="rounded-xl border border-slate-200 bg-[#FBFCFE] p-4 sm:col-span-2 sm:p-5">
                            <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-[0.12em] text-[#647B98]"><UserRound className="h-4 w-4 text-[#315B8A]" aria-hidden="true" />Account details</div>
                            <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                                <div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Account role</dt><dd className="mt-1 break-words text-sm font-semibold text-slate-800">{roleLabel}</dd></div>
                                <div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Account ID</dt><dd className="mt-1 text-sm font-semibold text-slate-800">{user.id ?? 'Not available'}</dd></div>
                            </dl>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};
