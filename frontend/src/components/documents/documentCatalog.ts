export interface DocumentServiceOffering {
    id: number;
    document_type: string;
    requirements: string[];
    published_fee_amount: string | null;
    details: string;
    is_active: boolean;
}

export const OTHER_DOCUMENT_TYPE = 'Other / Not listed';

export const formatPublishedFee = (amount: string | null | undefined) => {
    if (amount === null || amount === undefined || amount === '') return 'Confirm with Barangay staff';
    const numericAmount = Number(amount);
    if (!Number.isFinite(numericAmount)) return 'Confirm with Barangay staff';
    return numericAmount === 0 ? 'No fee' : `₱${numericAmount.toFixed(2)}`;
};
