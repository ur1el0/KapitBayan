import React from 'react';
import { SkipForward, CheckCircle, Bell } from 'lucide-react';
import type { QueueTicket } from './types';

interface QueueActionControlsProps {
    isUpdating: boolean;
    waitingCount: number;
    servingTicket: QueueTicket | null;
    onNextQueue: () => void;
    onMarkAsDone: () => void;
    onNotifyResident: () => void;
}

export const QueueActionControls: React.FC<QueueActionControlsProps> = ({
    isUpdating,
    waitingCount,
    servingTicket,
    onNextQueue,
    onMarkAsDone,
    onNotifyResident,
}) => {
    return (
        <div className="flex items-center gap-4">
            {/* Next Queue Button */}
            <button
                onClick={onNextQueue}
                disabled={isUpdating || waitingCount === 0}
                className="flex-1 bg-primary hover:bg-primary-hover active:bg-primary-hover text-primary-foreground py-3.5 px-6 rounded-2xl text-base font-bold shadow-sm flex items-center justify-center gap-2.5 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <SkipForward className="w-5 h-5 fill-current" />
                <span>{isUpdating ? 'Updating...' : 'Next Queue'}</span>
            </button>

            {/* Mark as Done Button */}
            <button
                onClick={onMarkAsDone}
                disabled={isUpdating || !servingTicket}
                className="flex-1 bg-white hover:bg-slate-50 border border-[#E2E8F0] text-[#0f172a] py-3.5 px-6 rounded-2xl text-base font-bold shadow-xs flex items-center justify-center gap-2.5 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <CheckCircle className="w-5 h-5 text-[#16A34A]" />
                <span>Mark as Done</span>
            </button>

            {/* Notify / Recall Button */}
            <button
                onClick={onNotifyResident}
                disabled={isUpdating || !servingTicket}
                aria-label="Page resident"
                className="flex-none bg-slate-100 hover:bg-slate-200 text-slate-700 py-3.5 px-5 rounded-2xl shadow-xs transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                title="Page the resident linked to the serving ticket"
            >
                <Bell className="w-5 h-5" />
            </button>
        </div>
    );
};
