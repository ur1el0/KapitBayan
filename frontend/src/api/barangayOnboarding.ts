import { axiosPrivate, axiosPublic } from './axios';

export type BarangayApplicationStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export interface BarangayApplication {
    id: number;
    name: string;
    municipality: string;
    province: string;
    applicant_name: string;
    applicant_position: string;
    applicant_email: string;
    applicant_phone: string;
    has_proof_of_authority: boolean;
    email_verified_at: string | null;
    proof_reviewed: boolean;
    admin_username: string;
    applicant_authorized: boolean;
    contact_consent: boolean;
    status: BarangayApplicationStatus;
    review_note: string;
    review_verified: boolean;
    reviewed_by_username: string | null;
    reviewed_at: string | null;
    created_barangay_id: number | null;
    created_admin_username: string | null;
    created_admin_email: string | null;
    has_applicant_account: boolean;
    admin_can_sign_in: boolean;
    created_at: string;
    updated_at: string;
}

export interface BarangayApplicationPage {
    count: number;
    next: string | null;
    previous: string | null;
    results: BarangayApplication[];
}

export interface BarangayApplicationInput {
    name: string;
    municipality: string;
    province: string;
    applicant_name: string;
    applicant_position: string;
    applicant_email: string;
    applicant_phone: string;
    proof_of_authority: File;
    password: string;
    password_confirm: string;
    applicant_authorized: true;
    contact_consent: true;
}

export async function submitBarangayApplication(payload: BarangayApplicationInput) {
    const form = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
        form.append(key, value instanceof Blob ? value : String(value));
    });
    const response = await axiosPublic.post('/auth/public/barangay-applications/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data as { id: number; status: 'PENDING'; created_at: string };
}

export async function verifyBarangayApplicationEmail(applicationId: number, token: string) {
    const response = await axiosPublic.post(
        `/auth/public/barangay-applications/${applicationId}/verify-email/`,
        { token },
    );
    return response.data as { detail: string };
}

export async function resendBarangayApplicationVerification(
    applicationId: number,
    applicantEmail: string,
) {
    const response = await axiosPublic.post(
        '/auth/public/barangay-applications/resend-verification/',
        { application_id: applicationId, applicant_email: applicantEmail },
    );
    return response.data as { detail: string };
}

export async function fetchBarangayApplications(
    status: BarangayApplicationStatus,
    page = 1,
): Promise<BarangayApplicationPage> {
    const response = await axiosPrivate.get('/auth/platform/barangay-applications/', {
        params: { status, page },
    });
    return response.data;
}

export async function approveBarangayApplication(
    applicationId: number,
    payload: { contact_verified: true; proof_reviewed: boolean; review_note?: string },
): Promise<BarangayApplication> {
    const response = await axiosPrivate.post(
        `/auth/platform/barangay-applications/${applicationId}/approve/`,
        payload,
    );
    return response.data;
}

export async function downloadBarangayApplicationProof(
    applicationId: number,
): Promise<{ url: string; filename: string }> {
    const response = await axiosPrivate.get(
        `/auth/platform/barangay-applications/${applicationId}/proof/`,
        { responseType: 'blob' },
    );
    const contentType = String(response.headers['content-type'] ?? '').split(';', 1)[0].trim().toLowerCase();
    const extension = contentType === 'application/pdf'
        ? 'pdf'
        : contentType === 'image/jpeg'
            ? 'jpg'
            : contentType === 'image/png'
                ? 'png'
                : 'bin';
    return {
        url: URL.createObjectURL(response.data as Blob),
        filename: `barangay-authority-proof-${applicationId}.${extension}`,
    };
}

export async function rejectBarangayApplication(
    applicationId: number,
    reason: string,
): Promise<BarangayApplication> {
    const response = await axiosPrivate.post(
        `/auth/platform/barangay-applications/${applicationId}/reject/`,
        { reason },
    );
    return response.data;
}
