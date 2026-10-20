export interface Resident {
    id: number;
    username?: string;
    email?: string;
    full_name: string;
    birth_date: string;
    voter_status: boolean;
    contact_number: string;
    purok?: string | number | null;
    address_details?: string | null;
    is_verified?: boolean;
    guardian?: number | null;
    philsys_id_number?: string | null;
    philsys_id_photo?: string | null;
    secondary_id_type?: string | null;
    secondary_id_photo?: string | null;
    utility_billing_type?: string | null;
    utility_billing_photo?: string | null;
}

export interface ImportSummary {
    imported: number;
    skipped_due_to_duplicate: number;
    errors: string[];
}

export function formatPurok(purok?: string | number | null): string {
    if (purok === null || purok === undefined) return 'Unassigned';
    const str = String(purok).trim();
    if (!str) return 'Unassigned';
    if (/^\d+$/.test(str)) {
        return `Purok ${str}`;
    }
    return str;
}
