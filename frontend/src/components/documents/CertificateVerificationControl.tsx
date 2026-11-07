import { useCallback, useEffect, useState } from 'react';
import { QRCodeCanvas } from 'qrcode.react';
import toast from 'react-hot-toast';
import { axiosPrivate } from '../../api/axios';

interface CertificateVerificationRecord {
    active: true;
    token: string;
    verification_url: string;
    issued_at: string;
}

interface CertificateVerificationControlProps {
    requestId: number;
    documentType: string;
}

export const CertificateVerificationControl = ({ requestId, documentType }: CertificateVerificationControlProps) => {
    const [record, setRecord] = useState<CertificateVerificationRecord | null>(null);
    const [confirmed, setConfirmed] = useState(false);
    const [loading, setLoading] = useState(true);
    const [working, setWorking] = useState(false);
    const [failed, setFailed] = useState(false);

    const endpoint = `/document-requests/${requestId}/certificate-verification/`;
    const loadRecord = useCallback(async () => {
        setLoading(true);
        try {
            const response = await axiosPrivate.get(endpoint);
            setRecord(response.data?.active ? response.data as CertificateVerificationRecord : null);
            setFailed(false);
        } catch {
            setFailed(true);
        } finally {
            setLoading(false);
        }
    }, [endpoint]);

    useEffect(() => {
        void loadRecord();
    }, [loadRecord]);

    const issueVerification = async () => {
        if (!confirmed) return;
        setWorking(true);
        try {
            const response = await axiosPrivate.post(endpoint, { confirm_paper_certificate_issued: true });
            setRecord(response.data as CertificateVerificationRecord);
            setConfirmed(false);
            toast.success('Certificate verification QR is ready to print.');
        } catch {
            toast.error('Could not create the certificate verification QR. Check the request status and try again.');
        } finally {
            setWorking(false);
        }
    };

    const revokeVerification = async () => {
        if (!window.confirm('Revoke this QR? Scans of the printed code will show that the record is no longer valid.')) return;
        setWorking(true);
        try {
            await axiosPrivate.delete(endpoint);
            setRecord(null);
            toast.success('Certificate verification QR revoked.');
        } catch {
            toast.error('Could not revoke this QR. Try again.');
        } finally {
            setWorking(false);
        }
    };

    return (
        <section className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4" aria-labelledby="certificate-verification-title">
            <div className="certificate-verification-screen-only">
                <h4 id="certificate-verification-title" className="text-sm font-bold text-slate-900">Paper certificate verification QR</h4>
                <p className="mt-1 text-xs leading-5 text-slate-600">
                    Create a QR label only after the Barangay has physically issued the paper certificate. The QR confirms the Barangay record; it is not the certificate itself.
                </p>
            </div>

            {loading ? <p className="certificate-verification-screen-only mt-3 text-xs text-slate-600" role="status">Checking verification record…</p> : failed ? (
                <div className="certificate-verification-screen-only mt-3 flex items-center gap-3 text-xs text-rose-700" role="alert">
                    <span>Could not load the verification record.</span>
                    <button type="button" onClick={() => void loadRecord()} className="rounded-md border border-rose-300 bg-white px-2.5 py-1.5 font-semibold">Retry</button>
                </div>
            ) : record ? (
                <>
                    <div className="certificate-verification-print-area mt-4 flex flex-col items-center rounded-lg border border-slate-200 bg-white p-4 text-center">
                        <p className="text-sm font-bold text-slate-900">Barangay-issued paper certificate</p>
                        <p className="mt-1 text-xs text-slate-700">{documentType}</p>
                        <div className="my-3 bg-white p-2">
                            <QRCodeCanvas value={record.verification_url} size={190} level="H" includeMargin title={`Verification QR for ${documentType}`} />
                        </div>
                        <p className="text-xs font-semibold text-slate-800">Scan to verify the Barangay issuance record</p>
                        <p className="mt-1 max-w-xs text-[10px] leading-4 text-slate-600">
                            This online record does not replace the signed paper certificate or verify its physical contents.
                        </p>
                    </div>
                    <div className="certificate-verification-screen-only mt-3 flex flex-wrap items-center gap-2">
                        <button type="button" onClick={() => window.print()} className="rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground">Print QR label</button>
                        <button type="button" onClick={() => void revokeVerification()} disabled={working} className="rounded-lg border border-rose-300 bg-white px-3 py-2 text-xs font-semibold text-rose-700 disabled:opacity-50">
                            {working ? 'Please wait…' : 'Revoke QR'}
                        </button>
                    </div>
                </>
            ) : (
                <div className="certificate-verification-screen-only mt-3 space-y-3">
                    <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                        <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} className="mt-1" />
                        <span>I confirm that the Barangay has issued the paper certificate for this released request.</span>
                    </label>
                    <button type="button" onClick={() => void issueVerification()} disabled={!confirmed || working} className="rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground disabled:opacity-50">
                        {working ? 'Creating QR…' : 'Create verification QR'}
                    </button>
                </div>
            )}
        </section>
    );
};
