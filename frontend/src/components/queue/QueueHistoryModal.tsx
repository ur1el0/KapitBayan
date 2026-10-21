import React from 'react';
import { X } from 'lucide-react';
import { useModalFocus } from '../../hooks/useModalFocus';
import type { QueueTicket } from './types';

interface QueueHistoryModalProps {
    isOpen: boolean;
    onClose: () => void;
    tickets: QueueTicket[];
    onDeleteTicket: (ticketId: number) => void;
}

export const QueueHistoryModal: React.FC<QueueHistoryModalProps> = ({
    isOpen,
    onClose,
    tickets,
    onDeleteTicket,
}) => {
    const dialogRef = useModalFocus<HTMLDivElement>(isOpen, onClose);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="queue-history-title"
                tabIndex={-1}
                className="bg-white rounded-2xl shadow-xl max-w-2xl w-full p-6 relative max-h-[85vh] flex flex-col animate-fade-in"
            >
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                    <h3 id="queue-history-title" className="text-lg font-bold text-[#0f172a]">Queue Activity History</h3>
                    <button
                        onClick={onClose}
                        aria-label="Close queue history"
                        className="text-slate-400 hover:text-slate-600 p-1"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="overflow-y-auto my-4 flex-1">
                    <table className="w-full text-left text-sm">
                        <thead>
                            <tr className="bg-slate-50 text-[#64748b] text-xs font-bold uppercase tracking-wider">
                                <th className="py-2.5 px-3">Ticket</th>
                                <th className="py-2.5 px-3">Resident / Service</th>
                                <th className="py-2.5 px-3">Status</th>
                                <th className="py-2.5 px-3">Time</th>
                                <th className="py-2.5 px-3 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {tickets.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="py-8 text-center text-slate-400">
                                        No ticket history available.
                                    </td>
                                </tr>
                            ) : (
                                tickets.map((t) => (
                                    <tr key={t.ticket_id} className="hover:bg-slate-50">
                                        <td className="py-2.5 px-3 font-bold text-primary-text">{t.ticket_number}</td>
                                        <td className="py-2.5 px-3">
                                            <div className="font-semibold text-slate-900">{t.resident_name || 'Walk-in'}</div>
                                            <div className="text-xs text-slate-500">{t.service_type}</div>
                                            {t.document_request_id && (
                                                <div className="text-xs text-blue-700 font-semibold mt-1">
                                                    Document request #{t.document_request_id}
                                                </div>
                                            )}
                                        </td>
                                        <td className="py-2.5 px-3">
                                            <span
                                                className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                                                    t.status === 'COMPLETED'
                                                        ? 'bg-green-100 text-green-800'
                                                        : t.status === 'SERVING'
                                                        ? 'bg-blue-100 text-blue-800'
                                                        : t.status === 'WAITING'
                                                        ? 'bg-amber-100 text-amber-800'
                                                        : 'bg-slate-100 text-slate-600'
                                                }`}
                                            >
                                                {t.status}
                                            </span>
                                        </td>
                                        <td className="py-2.5 px-3 text-xs text-slate-500 whitespace-nowrap">
                                            {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </td>
                                        <td className="py-2.5 px-3 text-right whitespace-nowrap">
                                            <button
                                                onClick={() => onDeleteTicket(t.ticket_id)}
                                                className="text-red-600 hover:text-red-800 font-semibold text-xs transition-colors"
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="pt-3 border-t border-slate-100 flex justify-end">
                    <button
                        onClick={onClose}
                        className="bg-slate-100 hover:bg-slate-200 text-slate-800 px-5 py-2 rounded-xl text-sm font-semibold transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};
