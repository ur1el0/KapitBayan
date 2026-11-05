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
    guardian_name?: string | null;
    guardian_username?: string | null;
    guardian_account_eligible?: boolean;
    guardian_relationship?: string | null;
    guardianship_evidence?: string | null;
    philsys_id_number?: string | null;
    philsys_id_photo?: string | null;
    secondary_id_type?: string | null;
    secondary_id_photo?: string | null;
    utility_billing_type?: string | null;
    utility_billing_photo?: string | null;
}

export function isMinorResident(birthDate: string): boolean {
    const date = new Date(`${birthDate}T00:00:00`);
    if (Number.isNaN(date.getTime())) return false;
    const today = new Date();
    let age = today.getFullYear() - date.getFullYear();
    if (
        today.getMonth() < date.getMonth() ||
        (today.getMonth() === date.getMonth() && today.getDate() < date.getDate())
    ) age--;
    return age < 18;
}

export function guardianRelationshipLabel(relationship?: string | null): string {
    switch (relationship) {
        case 'PARENT': return 'Parent';
        case 'COURT_APPOINTED': return 'Court-appointed guardian';
        case 'OTHER_AUTHORIZED': return 'Other authorized guardian';
        default: return 'Not provided';
    }
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
