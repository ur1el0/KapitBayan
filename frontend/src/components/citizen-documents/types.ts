export interface PaymentRecipient {
    id: number;
    provider: string;
    provider_label: string;
    display_name: string;
    recipient_name: string;
    recipient_identifier: string;
    instructions: string;
}

export interface DocumentRequest {
    id: number;
    offering_id?: number | null;
    document_type: string;
    requirements_snapshot?: string[];
    published_fee_amount_snapshot?: string | null;
    offering_details_snapshot?: string;
    purpose: string;
    status: string;
    fee_amount?: number | string | null;
    fee_assessment_status?: 'AWAITING_ASSESSMENT' | 'ASSESSED' | 'WAIVED' | 'STATUTORY_EXEMPT' | string;
    fee_assessed_by_name?: string | null;
    fee_assessed_at?: string | null;
    fee_waiver_reason?: string;
    payment_method?: string;
    payment_reference?: string;
    payment_status?: string;
    payment_review_note?: string;
    payment_recipient?: number | null;
    payment_recipient_name_snapshot?: string | null;
    payment_recipient_identifier_snapshot?: string | null;
    payment_instructions_snapshot?: string | null;
    payment_proof_url?: string | null;
    payment_transacted_at?: string | null;
    admin_notes?: string;
    or_number?: string;
    created_at: string;
}
