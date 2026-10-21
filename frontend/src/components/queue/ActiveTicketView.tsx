import React from 'react';

interface ActiveTicketViewProps {
    servingTicket: any | null;
}

export const ActiveTicketView: React.FC<ActiveTicketViewProps> = ({ servingTicket }) => {
    return (
        <div className="bg-surface rounded-large p-6 shadow-xs border border-border/80 flex flex-col justify-between h-full">
            <div>
                <div className="flex items-center justify-between">
                    <span className="text-neutral-muted text-xs font-semibold uppercase tracking-wider">
                        Ticket Number
                    </span>
                    <span className="bg-feedback-success-soft text-feedback-success-strong text-xs font-bold px-3 py-1 rounded-pill flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-pill bg-feedback-success-strong animate-pulse"></span>
                        NOW SERVING
                    </span>
                </div>

                <div className="my-5">
                    <h2 className="text-5xl lg:text-6xl font-black text-primary-text tracking-tight">
                        {servingTicket ? servingTicket.ticket_number : '--'}
                    </h2>
                </div>
            </div>

            <div className="bg-surface-queue rounded-medium p-3.5 flex items-center gap-3">
                <div className="w-9 h-9 rounded-small bg-border-strong text-neutral-secondary-strong font-bold flex items-center justify-center text-sm shrink-0">
                    {servingTicket?.resident_name
                        ? servingTicket.resident_name.charAt(0).toUpperCase()
                        : servingTicket
                        ? 'R'
                        : '-'}
                </div>
                <div className="min-w-0 flex-1">
                    <div className="text-[10px] text-neutral-muted font-medium leading-none uppercase">
                        {servingTicket ? servingTicket.service_type : 'Status'}
                    </div>
                    <div className="text-sm font-bold text-neutral-primary truncate mt-0.5">
                        {servingTicket ? (servingTicket.resident_name || 'Walk-in Resident') : 'No resident currently being served'}
                    </div>
                    {servingTicket?.document_request_id && (
                        <div className="text-xs text-blue-700 font-semibold mt-1">
                            Document request #{servingTicket.document_request_id}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
