import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { axiosPublic } from '../../api/axios';
import { getSafeApiErrorMessage } from '../../api/error-message';
import { Shield } from 'lucide-react';
import { useLanguage } from '../../context/language-context';
import { LanguageSwitcher } from '../../components/language/LanguageSwitcher';
import { TextField } from '../../components/ui/TextField';
import { Button } from '../../components/ui/Button';
import {
    RegisterHeroBanner,
    ResidentVerificationUploads,
    BarangaySelectField,
    type PublicBarangay,
} from '../../components/auth/register';

export const Register: React.FC = () => {
    const { t } = useLanguage();
    // Common fields
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    // Resident-specific fields
    const [username, setUsername] = useState('');
    const [birthDate, setBirthDate] = useState('');
    const [contactNumber, setContactNumber] = useState('');
    const [purok, setPurok] = useState('');
    const [addressDetails, setAddressDetails] = useState('');
    const [guardianId, setGuardianId] = useState('');

    // Verification proofs state
    const [isVerificationExpanded, setIsVerificationExpanded] = useState(false);
    const [philsysIdNumber, setPhilsysIdNumber] = useState('');
    const [philsysPhoto, setPhilsysPhoto] = useState<File | null>(null);
    const [utilityBillingType, setUtilityBillingType] = useState('Electric Bill');
    const [utilityBillingPhoto, setUtilityBillingPhoto] = useState<File | null>(null);
    const [secondaryIdType, setSecondaryIdType] = useState('');
    const [secondaryIdPhoto, setSecondaryIdPhoto] = useState<File | null>(null);

    // Barangay selection fields
    const [barangayId, setBarangayId] = useState('');
    const [barangays, setBarangays] = useState<PublicBarangay[]>([]);
    const [loadingBarangays, setLoadingBarangays] = useState(true);
    const [barangayDirectoryError, setBarangayDirectoryError] = useState('');
    const [dataPrivacyConsent, setDataPrivacyConsent] = useState(false);

    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const barangayRequestId = React.useRef(0);

    const navigate = useNavigate();

    const fetchBarangays = React.useCallback(async () => {
        const requestId = ++barangayRequestId.current;
        setLoadingBarangays(true);

        try {
            const response = await axiosPublic.get('/auth/public/barangays/');
            const data = Array.isArray(response.data) ? response.data : response.data?.results;
            if (!Array.isArray(data)) {
                throw new Error('Unexpected approved barangays response');
            }
            if (requestId !== barangayRequestId.current) return;
            setBarangays(data);
            setBarangayDirectoryError('');
        } catch {
            if (requestId !== barangayRequestId.current) return;
            setBarangays([]);
            setBarangayDirectoryError(t('Approved barangays could not be loaded. Please try again.'));
        } finally {
            if (requestId === barangayRequestId.current) {
                setLoadingBarangays(false);
            }
        }
    }, [t]);

    React.useEffect(() => {
        void fetchBarangays();
        return () => {
            barangayRequestId.current += 1;
        };
    }, [fetchBarangays]);

    // Dynamically calculate if applicant is under 18
    const isMinor = React.useMemo(() => {
        if (!birthDate) return false;
        const birth = new Date(birthDate);
        const today = new Date();
        let age = today.getFullYear() - birth.getFullYear();
        const m = today.getMonth() - birth.getMonth();
        if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) {
            age--;
        }
        return age < 18;
    }, [birthDate]);

    const handleRegister = async (e: React.SubmitEvent<HTMLElement>) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (password !== confirmPassword) {
            setError(t('Passwords do not match.'));
            return;
        }

        if (!purok.trim()) {
            setError(t('Please enter your Purok or Zone.'));
            return;
        }

        if (
            !philsysPhoto &&
            !utilityBillingPhoto &&
            !secondaryIdPhoto
        ) {
            setError(t('Upload at least one ID or proof of residency photo to register.'));
            setIsVerificationExpanded(true);
            return;
        }

        setLoading(true);

        try {
            // Resident Registration Pipeline (Multipart FormData)
            const formData = new FormData();
            formData.append('full_name', fullName.trim());
            formData.append('username', username.trim());
            formData.append('email', email.trim().toLowerCase());
            formData.append('password', password);
            formData.append('birth_date', birthDate);
            formData.append('purok', purok.trim());
            if (addressDetails.trim()) {
                formData.append('address_details', addressDetails.trim());
            }
            formData.append('voter_status', 'false');
            formData.append(
                'privacy_consent',
                dataPrivacyConsent ? 'true' : 'false',
            );
            formData.append('privacy_consent_version', 'resident-v1');

            if (contactNumber.trim()) {
                formData.append('contact_number', contactNumber.trim());
            }
            if (guardianId.trim()) {
                formData.append('guardian_id', guardianId.trim());
            }
            if (barangayId.trim()) {
                const parsedId = parseInt(barangayId.trim(), 10);
                if (!isNaN(parsedId)) {
                    formData.append('barangay_id', String(parsedId));
                }
            }

            // PhilSys Identity
            if (philsysIdNumber.trim()) {
                formData.append('philsys_id_number', philsysIdNumber.trim());
            }
            if (philsysPhoto) {
                formData.append('philsys_id_photo', philsysPhoto);
            }

            // Utility Proof of Residency
            if (utilityBillingType.trim()) {
                formData.append('utility_billing_type', utilityBillingType.trim());
            }
            if (utilityBillingPhoto) {
                formData.append('utility_billing_photo', utilityBillingPhoto);
            }

            // Secondary Valid ID (Optional)
            if (secondaryIdType.trim()) {
                formData.append('secondary_id_type', secondaryIdType.trim());
            }
            if (secondaryIdPhoto) {
                formData.append('secondary_id_photo', secondaryIdPhoto);
            }

            await axiosPublic.post('/auth/register/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setSuccess('Resident account created successfully! Redirecting to login...');

            setTimeout(() => {
                navigate('/login');
            }, 2000);
        } catch (err: any) {
            if (!err.response || err.response.status >= 500) {
                setError(getSafeApiErrorMessage(
                    err,
                    "We couldn't create your account. Check your connection and try again.",
                ));
                return;
            }
            if (err.response?.data) {
                const data = err.response.data;
                if (typeof data === 'string') {
                    setError(data);
                } else if (data.detail) {
                    setError(data.detail);
                } else if (data.username) {
                    setError(Array.isArray(data.username) ? data.username[0] : data.username);
                } else if (data.email) {
                    setError(Array.isArray(data.email) ? data.email[0] : data.email);
                } else if (data.password) {
                    setError(Array.isArray(data.password) ? data.password[0] : data.password);
                } else if (data.birth_date) {
                    setError(Array.isArray(data.birth_date) ? data.birth_date[0] : data.birth_date);
                } else if (data.contact_number) {
                    setError(Array.isArray(data.contact_number) ? data.contact_number[0] : data.contact_number);
                } else if (data.guardian_id) {
                    setError(Array.isArray(data.guardian_id) ? data.guardian_id[0] : data.guardian_id);
                } else {
                    const firstKey = Object.keys(data)[0];
                    setError(Array.isArray(data[firstKey]) ? data[firstKey][0] : String(data[firstKey]));
                }
            } else {
                setError(t('Registration failed. Please verify submitted details and try again.'));
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col md:flex-row bg-[#F6F8FC] font-sans">
            {/* Left Sidebar Banner */}
            <RegisterHeroBanner
            />

            {/* Right Registration Form */}
            <div className="w-full md:w-7/12 lg:w-[60%] flex flex-col justify-center items-center px-6 py-8 sm:p-12 lg:p-16 overflow-y-auto">
                <div className="w-full max-w-md">
                    <div className="mb-5 flex justify-end">
                        <LanguageSwitcher />
                    </div>
                    {/* Header */}
                    <div className="mb-6">
                        <div className="flex items-center gap-2 mb-2">
                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-sky-100 text-sky-900">
                                Resident
                            </span>
                        </div>
                        <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">
                            {t('Resident Registration')}
                        </h2>
                        <p className="text-slate-500 text-sm mt-1">
                            {t('Complete your registration details to access barangay services.')}
                        </p>
                    </div>

                    {/* Alerts */}
                    {error && (
                        <div role="alert" className="mb-5 bg-red-50/90 border border-red-200 rounded-xl p-3.5 flex items-center gap-3">
                            <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p className="text-sm font-medium text-red-700">{error}</p>
                        </div>
                    )}

                    {success && (
                        <div className="mb-5 bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 flex items-center gap-3">
                            <svg className="w-5 h-5 text-emerald-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                            </svg>
                            <p className="text-sm font-medium text-emerald-700">{success}</p>
                        </div>
                    )}

                    <form className="space-y-4" onSubmit={handleRegister}>
                            <TextField
                                label={t('FULL NAME (AS IN ID)')}
                                type="text"
                                required
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                placeholder="e.g. Juan Dela Cruz"
                            />

                            <TextField
                                label={t('USERNAME')}
                                type="text"
                                required
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="juandelacruz"
                            />

                            <TextField
                                label={t('EMAIL ADDRESS')}
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="juan@example.com"
                            />

                            {/* Resident Mode: Contact Number & Date of Birth */}
                            <TextField
                                label={t('CONTACT NUMBER')}
                                type="tel"
                                value={contactNumber}
                                onChange={(e) => setContactNumber(e.target.value)}
                                placeholder="0917 123 4567"
                            />
                            <TextField
                                label={t('DATE OF BIRTH')}
                                type="date"
                                required
                                value={birthDate}
                                onChange={(e) => setBirthDate(e.target.value)}
                            />

                            {/* Resident Mode: Identity & Residency Verification Proofs */}
                            <ResidentVerificationUploads
                                isExpanded={isVerificationExpanded}
                                onToggleExpand={() => setIsVerificationExpanded((prev) => !prev)}
                                philsysIdNumber={philsysIdNumber}
                                onPhilsysIdNumberChange={setPhilsysIdNumber}
                                philsysPhoto={philsysPhoto}
                                onPhilsysPhotoChange={setPhilsysPhoto}
                                utilityBillingType={utilityBillingType}
                                onUtilityBillingTypeChange={setUtilityBillingType}
                                utilityBillingPhoto={utilityBillingPhoto}
                                onUtilityBillingPhotoChange={setUtilityBillingPhoto}
                                secondaryIdType={secondaryIdType}
                                onSecondaryIdTypeChange={(val) => {
                                    setSecondaryIdType(val);
                                    if (!val) setSecondaryIdPhoto(null);
                                }}
                                secondaryIdPhoto={secondaryIdPhoto}
                                onSecondaryIdPhotoChange={setSecondaryIdPhoto}
                            />

                            {/* Minor Guardian Constraint Box */}
                            {isMinor && (
                                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2 animate-fadeIn">
                                    <div className="flex items-center gap-2 text-amber-900 text-xs font-bold uppercase tracking-wider">
                                        <Shield className="w-4 h-4 text-amber-600 shrink-0" />
                                        <span>{t('Parent / Legal Guardian Verification Required')}</span>
                                    </div>
                                    <p className="text-[11px] text-amber-800 leading-relaxed">
                                        {t("Applicants under 18 must link their registration to an already registered parent or legal guardian's account.")}
                                    </p>
                                    <TextField
                                        label={t("GUARDIAN'S REGISTERED USERNAME *")}
                                        type="text"
                                        required
                                        value={guardianId}
                                        onChange={(e) => setGuardianId(e.target.value)}
                                        placeholder="e.g. resident_dupay"
                                    />
                                </div>
                            )}

                            {/* Universal Barangay Selection Dropdown */}
                            <BarangaySelectField
                                barangayId={barangayId}
                                onBarangayIdChange={setBarangayId}
                                barangays={barangays}
                                loadingBarangays={loadingBarangays}
                                barangayDirectoryError={barangayDirectoryError}
                                onRetry={fetchBarangays}
                                isAdminMode={false}
                            />

                            <TextField
                                label={t('PUROK / ZONE')}
                                type="text"
                                required
                                maxLength={100}
                                value={purok}
                                onChange={(e) => setPurok(e.target.value)}
                                placeholder="e.g. Purok 3 or Zone 2"
                            />
                            <TextField
                                label={t('HOUSE / STREET / LANDMARK (OPTIONAL)')}
                                type="text"
                                maxLength={255}
                                value={addressDetails}
                                onChange={(e) => setAddressDetails(e.target.value)}
                                placeholder="e.g. House 12, Mabini Street, near chapel"
                            />

                            {/* Passwords */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <TextField
                                    label="PASSWORD"
                                    type="password"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                />
                                <TextField
                                    label={t('CONFIRM PASSWORD')}
                                    type="password"
                                    required
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    placeholder="••••••••"
                                />
                            </div>

                            {/* Resident Mode: Data Privacy Consent */}
                            <div className="pt-1">
                                <label className="flex items-start gap-2.5 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        required
                                        checked={dataPrivacyConsent}
                                        onChange={(e) => setDataPrivacyConsent(e.target.checked)}
                                        className="mt-0.5 w-4 h-4 text-[#0284C7] rounded focus:ring-0 border-slate-300 cursor-pointer shrink-0"
                                    />
                                    <span className="text-xs text-slate-600 leading-relaxed">
                                        {t('I consent to provide my personal data as a resident for barangay verification, in accordance with the')} <strong>RA 10173 Data Privacy Act</strong>.
                                    </span>
                                </label>
                            </div>

                            {/* Submit Button */}
                            <div className="pt-2">
                                <Button
                                    type="submit"
                                    loading={loading}
                                    loadingText={t('Creating Resident Account...')}
                                    disabled={
                                        loadingBarangays || barangays.length === 0 || !dataPrivacyConsent
                                    }
                                >
                                    {t('Create Resident Account')}
                                </Button>
                            </div>

                            <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-center text-xs leading-5 text-slate-600">
                                {t('Field Official accounts are created by their Barangay Admin. Barangay Admin accounts are provisioned by the system operator after review.')}
                            </p>

                            {/* Back to Login */}
                            <div className="text-center pt-1">
                                <p className="text-xs text-slate-500 font-medium">
                                    {t('Already have an account?')}{' '}
                                    <Link to="/login" className="font-bold text-slate-900 hover:text-[#0284C7] hover:underline transition-colors">
                                        {t('Log in here')}
                                    </Link>
                                </p>
                            </div>
                    </form>
                </div>
            </div>
        </div>
    );
};
