export interface QueueTicket {
    ticket_id: number;
    ticket_number: string;
    resident_name?: string;
    has_resident_account?: boolean;
    service_type: string;
    notes?: string | null;
    document_request_id?: number | null;
    document_request_type?: string | null;
    document_request_status?: string | null;
    priority_status?: string;
    is_priority?: boolean;
    status: string;
    created_at: string;
    updated_at?: string;
}
