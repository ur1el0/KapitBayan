export interface DashboardSummary {
    total_residents: number;
    document_requests: {
        total: number;
        pending: number;
        approved: number;
        rejected: number;
        released: number;
        total_revenue?: number;
    };
    issue_reports: {
        total: number;
        pending: number;
        in_progress: number;
        resolved: number;
        urgency_breakdown: {
            low: number;
            medium: number;
            high: number;
            urgent: number;
        };
        scenario_breakdown: {
            peace_and_order: number;
            public_health: number;
            infrastructure: number;
            environment: number;
            other: number;
        };
        time_of_day: {
            night_time: number;
            day_time: number;
        };
    };
    queue_activity: {
        total_today: number;
        serving_now: string | null;
        waiting_count: number;
    };
    demographics?: {
        purok_distribution: Record<string, number>;
        age_demographics: {
            youth: number;
            young_adult: number;
            adult: number;
            senior: number;
        };
    };
}

export interface ActivityItem {
    id: number;
    title: string;
    description: string;
    location: string;
    event_datetime: string;
    created_at: string;
}

export interface NamedValue {
    name: string;
    value: number;
}

export interface NamedCount {
    name: string;
    count: number;
}

export interface AccomplishmentDocumentBreakdown {
    document_type: string;
    count: number;
}

export interface AccomplishmentReport {
    barangay_name: string;
    municipality: string;
    province: string;
    captain_name: string;
    year: number;
    month: number;
    period_mode?: 'month' | 'range';
    start_date?: string;
    end_date?: string;
    period_label: string;
    generated_at: string;
    included_metrics?: string[];
    filter_summary?: string;
    residents_rbi: {
        new_registered_residents: number;
        new_verified_residents: number;
        approved_rbi_transfers: number;
        total_active_verified_residents: number;
    };
    certificates_issuance: {
        total_requests: number;
        total_issued: number;
        fee_waived_or_exempt_count: number;
        by_document_type: AccomplishmentDocumentBreakdown[];
    };
    community_services: {
        issues_submitted: number;
        issues_resolved: number;
        aid_requests_submitted: number;
        aid_requests_approved: number;
        equipment_requests_fulfilled: number;
        equipment_requests_returned: number;
    };
    communications_activities: {
        announcements_published: number;
        activities_conducted: number;
    };
}
