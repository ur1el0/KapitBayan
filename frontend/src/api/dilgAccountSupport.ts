import { axiosPrivate } from './axios';

export type AccountSupportReason =
    | 'INCORRECT_CONTACT'
    | 'LOCKED_OUT'
    | 'SECURITY_CONCERN'
    | 'STATUS_CORRECTION'
    | 'OTHER_VERIFIED_SUPPORT';

export interface DILGAccount {
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
    results: DILGAccount[];
}

export interface AccountFilters {
    search?: string;
    role?: DILGAccount['role'] | '';
    active?: boolean;
    page?: number;
}

export async function fetchDILGAccounts(filters: AccountFilters = {}): Promise<AccountPage> {
    const response = await axiosPrivate.get('/auth/dilg/accounts/', {
        params: {
            ...(filters.search ? { search: filters.search } : {}),
            ...(filters.role ? { role: filters.role } : {}),
            ...(filters.active === undefined ? {} : { active: filters.active }),
            page: filters.page ?? 1,
        },
    });
    return response.data;
}

export async function correctDILGAccountEmail(
    accountId: number,
    payload: { email: string; contact_verified: true; reason: AccountSupportReason },
): Promise<DILGAccount> {
    const response = await axiosPrivate.patch(`/auth/dilg/accounts/${accountId}/`, payload);
    return response.data;
}

export async function sendDILGAccountRecoveryLink(
    accountId: number,
    payload: { contact_verified: true; reason: AccountSupportReason },
): Promise<void> {
    await axiosPrivate.post(`/auth/dilg/accounts/${accountId}/send-password-link/`, payload);
}

export async function setDILGAccountActive(
    accountId: number,
    payload: { is_active: boolean; reason: AccountSupportReason },
): Promise<DILGAccount> {
    const response = await axiosPrivate.post(`/auth/dilg/accounts/${accountId}/set-active/`, payload);
    return response.data;
}
