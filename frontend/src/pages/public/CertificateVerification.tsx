import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { CheckCircle2, CircleHelp, ShieldCheck, XCircle } from 'lucide-react';
import { axiosPublic } from '../../api/axios';
import { LanguageSwitcher } from '../../components/language/LanguageSwitcher';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { useLanguage } from '../../context/language-context';

interface VerificationResult {
    valid: boolean;
    barangay_name?: string;
    document_type?: string;
    issued_at?: string;
}

export const CertificateVerification = () => {
    const { t } = useLanguage();
    const { token } = useParams<{ token: string }>();
    const [result, setResult] = useState<VerificationResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [failed, setFailed] = useState(false);
    const [retrying, setRetrying] = useState(false);

    const verify = useCallback(async (isRetry = false) => {
        if (!token) {
            setResult({ valid: false });
            setLoading(false);
            return;
        }
        if (isRetry) setRetrying(true);
        try {
            const response = await axiosPublic.get(`/public/certificate-verifications/${encodeURIComponent(token)}/`);
            setResult(response.data as VerificationResult);
            setFailed(false);
        } catch {
            setFailed(true);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    }, [token]);

    useEffect(() => {
        void verify();
    }, [verify]);

    useEffect(() => {
        const existingRobotsMeta = document.querySelector<HTMLMetaElement>('meta[name="robots"]');
        const previousContent = existingRobotsMeta?.content;
        const robotsMeta = existingRobotsMeta ?? document.createElement('meta');
        robotsMeta.name = 'robots';
        robotsMeta.content = 'noindex, nofollow';
        if (!existingRobotsMeta) document.head.appendChild(robotsMeta);

        return () => {
            if (existingRobotsMeta && previousContent !== undefined) {
                existingRobotsMeta.content = previousContent;
            } else {
                robotsMeta.remove();
            }
        };
    }, []);

    const issuedDate = result?.issued_at
        ? new Date(result.issued_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
        : null;

    return (
        <main className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900">
            <div className="mx-auto max-w-xl space-y-5">
                <header className="rounded-2xl bg-primary p-6 text-primary-foreground">
                    <div className="mb-4 flex justify-end"><LanguageSwitcher compact /></div>
                    <div className="flex items-center gap-3">
                        <ShieldCheck aria-hidden="true" />
                        <div>
                            <p className="text-xs font-bold uppercase tracking-wider opacity-80">{t('KapitBayan certificate lookup')}</p>
                            <h1 className="text-2xl font-bold">{t('Paper certificate verification')}</h1>
                        </div>
                    </div>
                </header>

                {loading ? <p role="status" className="rounded-xl bg-white p-5 text-sm text-slate-600">{t('Checking the Barangay record…')}</p> : failed ? (
                    <InlineErrorState
                        message={t('Verification is temporarily unavailable. Try again when you have a connection.')}
                        onRetry={() => { void verify(true); }}
                        retrying={retrying}
                    />
                ) : result?.valid ? (
                    <section className="rounded-2xl border border-emerald-200 bg-white p-6 shadow-sm" aria-labelledby="certificate-valid-title">
                        <div className="flex items-center gap-3 text-emerald-800">
                            <CheckCircle2 className="h-8 w-8 shrink-0" aria-hidden="true" />
                            <h2 id="certificate-valid-title" className="text-xl font-bold">{t('Valid Barangay issuance record')}</h2>
                        </div>
                        <dl className="mt-5 space-y-3 text-sm">
                            <div><dt className="font-semibold text-slate-500">{t('Issuing Barangay')}</dt><dd className="mt-1">{result.barangay_name}</dd></div>
                            <div><dt className="font-semibold text-slate-500">{t('Certificate type')}</dt><dd className="mt-1">{result.document_type}</dd></div>
                            {issuedDate && <div><dt className="font-semibold text-slate-500">{t('Record issued')}</dt><dd className="mt-1">{issuedDate}</dd></div>}
                        </dl>
                        <p className="mt-5 rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                            {t('This confirms that the Barangay recorded this certificate as issued. It does not verify the holder’s identity, replace the signed paper certificate, or verify the paper’s physical contents.')}
                        </p>
                    </section>
                ) : (
                    <section className="rounded-2xl border border-rose-200 bg-white p-6 shadow-sm" aria-labelledby="certificate-invalid-title">
                        <div className="flex items-center gap-3 text-rose-800">
                            {result ? <XCircle className="h-8 w-8 shrink-0" aria-hidden="true" /> : <CircleHelp className="h-8 w-8 shrink-0" aria-hidden="true" />}
                            <h2 id="certificate-invalid-title" className="text-xl font-bold">{t('Record not verified')}</h2>
                        </div>
                        <p className="mt-4 text-sm leading-6 text-slate-600">{t('This QR does not currently match an active Barangay issuance record. Contact the issuing Barangay to confirm the paper certificate.')}</p>
                    </section>
                )}
            </div>
        </main>
    );
};
