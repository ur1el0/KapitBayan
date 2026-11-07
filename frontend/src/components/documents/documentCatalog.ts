export interface DocumentServiceOffering {
    id: number;
    document_type: string;
    requirements: string[];
    published_fee_amount: string | null;
    details: string;
    is_active: boolean;
}

export const COMMON_DOCUMENT_REQUIREMENTS = [
    'Government ID or proof of residency',
    'Community Tax Certificate (Cedula)',
    'Proof of address',
    'Supporting document for the stated purpose',
    'Parent or guardian proof of authority',
] as const;

export function splitDocumentRequirements(requirements: string[] = []) {
    const commonByNormalizedLabel = new Map(
        COMMON_DOCUMENT_REQUIREMENTS.map((requirement) => [requirement.toLocaleLowerCase(), requirement]),
    );
    const selectedCommon: string[] = [];
    const customRequirements: string[] = [];
    const seenCommon = new Set<string>();

    requirements.forEach((item) => {
        const normalized = item.trim().toLocaleLowerCase();
        const common = commonByNormalizedLabel.get(normalized);
        if (common) {
            if (!seenCommon.has(normalized)) selectedCommon.push(common);
            seenCommon.add(normalized);
        } else if (item.trim()) {
            customRequirements.push(item.trim());
        }
    });

    return { selectedCommon, customRequirements };
}

export function combineDocumentRequirements(selectedCommon: string[], customText: string) {
    const requirements = [...selectedCommon, ...customText.split('\n')]
        .map((requirement) => requirement.trim())
        .filter(Boolean);
    const seen = new Set<string>();

    return requirements.filter((requirement) => {
        const normalized = requirement.toLocaleLowerCase();
        if (seen.has(normalized)) return false;
        seen.add(normalized);
        return true;
    });
}

export const OTHER_DOCUMENT_TYPE = 'Other / Not listed';

export const formatPublishedFee = (amount: string | null | undefined) => {
    if (amount === null || amount === undefined || amount === '') return 'Confirm with Barangay staff';
    const numericAmount = Number(amount);
    if (!Number.isFinite(numericAmount)) return 'Confirm with Barangay staff';
    return numericAmount === 0 ? 'No fee' : `₱${numericAmount.toFixed(2)}`;
};
