export interface QueueTicket {
    ticket_id: number;
    ticket_number: string;
    resident_name?: string;
    service_type: string;
    document_request_id?: number | null;
    document_request_type?: string | null;
    priority_status?: string;
    is_priority?: boolean;
    status: string;
    created_at: string;
    updated_at?: string;
}
