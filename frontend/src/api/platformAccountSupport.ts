import { axiosPrivate } from './axios';

export type AccountSupportReason =
    | 'INCORRECT_CONTACT'
    | 'LOCKED_OUT'
    | 'SECURITY_CONCERN'
    | 'STATUS_CORRECTION'
    | 'OTHER_VERIFIED_SUPPORT';

export type AccountErasureReason =
    | 'ACCOUNT_HOLDER_REQUEST'
    | 'DUPLICATE_ACCOUNT'
    | 'SECURITY_OR_FRAUD'
    | 'OTHER_APPROVED_REASON';

export interface PlatformAccount {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    full_name: string;
    role: 'RESIDENT' | 'FIELD_OFFICIAL' | 'ADMIN';
    is_active: boolean;
    barangay_id: number | null;
    barangay_name: string | null;
    barangay_municipality: string | null;
    barangay_province: string | null;
}

export interface AccountPage {
    count: number;
    next: string | null;
    previous: string | null;
    results: PlatformAccount[];
}

export interface AccountFilters {
    search?: string;
    role?: PlatformAccount['role'] | '';
    active?: boolean;
    page?: number;
}

export async function fetchPlatformAccounts(filters: AccountFilters = {}): Promise<AccountPage> {
    const response = await axiosPrivate.get('/auth/platform/accounts/', {
        params: {
            ...(filters.search ? { search: filters.search } : {}),
            ...(filters.role ? { role: filters.role } : {}),
            ...(filters.active === undefined ? {} : { active: filters.active }),
            page: filters.page ?? 1,
        },
    });
    return response.data;
}

export async function correctPlatformAccountEmail(
    accountId: number,
    payload: { email: string; contact_verified: true; reason: AccountSupportReason },
): Promise<PlatformAccount> {
    const response = await axiosPrivate.patch(`/auth/platform/accounts/${accountId}/`, payload);
    return response.data;
}

export async function sendPlatformAccountRecoveryLink(
    accountId: number,
    payload: { contact_verified: true; reason: AccountSupportReason },
): Promise<void> {
    await axiosPrivate.post(`/auth/platform/accounts/${accountId}/send-password-link/`, payload);
}

export async function setPlatformAccountActive(
    accountId: number,
    payload: { is_active: boolean; reason: AccountSupportReason },
): Promise<PlatformAccount> {
    const response = await axiosPrivate.post(`/auth/platform/accounts/${accountId}/set-active/`, payload);
    return response.data;
}

export async function erasePlatformAccount(
    accountId: number,
    payload: { reason: AccountErasureReason; confirm_username: string },
): Promise<void> {
    await axiosPrivate.post(`/auth/platform/accounts/${accountId}/erase/`, payload);
}
