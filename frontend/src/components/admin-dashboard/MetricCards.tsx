import React from 'react';
import { Banknote, FileText, Hourglass, Users } from 'lucide-react';
import type { DashboardSummary } from './types';
import { useLanguage } from '../../context/language-context';

interface MetricCardsProps {
    loading: boolean;
    summary: DashboardSummary | null;
}

const MetricCardSkeleton = () => (
    <div className="bg-surface rounded-large p-6 shadow-sm border border-border/80 flex flex-col justify-between animate-pulse">
        <div>
            <div className="w-10 h-10 rounded-medium bg-border"></div>
            <div className="h-3 w-32 bg-border rounded mt-5"></div>
            <div className="h-8 w-16 bg-border rounded mt-3"></div>
        </div>
    </div>
);

export const MetricCards: React.FC<MetricCardsProps> = ({ loading, summary }) => {
    const { t } = useLanguage();

    return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {loading ? (
            <>
                <MetricCardSkeleton />
                <MetricCardSkeleton />
                <MetricCardSkeleton />
                <MetricCardSkeleton />
            </>
        ) : (
            <>
                <div className="bg-surface rounded-large p-6 shadow-xs border border-border/80 flex flex-col justify-between hover:-translate-y-1 hover:shadow-md transition-all duration-300">
                    <div>
                        <div className="w-10 h-10 rounded-medium bg-primary/10 text-primary-text flex items-center justify-center">
                            <Users className="w-5 h-5" />
                        </div>
                        <h3 className="text-neutral-muted text-xs font-semibold uppercase tracking-wider mt-4">
                            {t('Total Registered Residents')}
                        </h3>
                        <p className="text-3xl font-extrabold text-neutral-primary mt-1">
                            {summary?.total_residents?.toLocaleString() ?? '--'}
                        </p>
                    </div>
                </div>

                <div className="bg-surface rounded-large p-6 shadow-xs border border-border/80 flex flex-col justify-between hover:-translate-y-1 hover:shadow-md transition-all duration-300">
                    <div>
                        <div className="w-10 h-10 rounded-medium bg-feedback-danger-soft text-feedback-danger-text-strong flex items-center justify-center">
                            <FileText className="w-5 h-5" />
                        </div>
                        <h3 className="text-neutral-muted text-xs font-semibold uppercase tracking-wider mt-4">
                            {t('Pending Requests')}
                        </h3>
                        <p className="text-3xl font-extrabold text-neutral-primary mt-1">
                            {summary !== null ? summary.document_requests.pending : '--'}
                        </p>
                    </div>
                </div>

                <div className="bg-surface rounded-large p-6 shadow-xs border border-border/80 flex flex-col justify-between hover:-translate-y-1 hover:shadow-md transition-all duration-300">
                    <div>
                        <div className="w-10 h-10 rounded-medium bg-feedback-warning-soft text-feedback-warning flex items-center justify-center">
                            <Hourglass className="w-5 h-5" />
                        </div>
                        <h3 className="text-neutral-muted text-xs font-semibold uppercase tracking-wider mt-4">
                            {t('Active Issues (In Progress)')}
                        </h3>
                        <p className="text-3xl font-extrabold text-neutral-primary mt-1">
                            {summary !== null ? summary.issue_reports.in_progress : '--'}
                        </p>
                    </div>
                </div>

                <div className="bg-surface rounded-large p-6 shadow-xs border border-border/80 flex flex-col justify-between hover:-translate-y-1 hover:shadow-md transition-all duration-300">
                    <div>
                        <div className="w-10 h-10 rounded-medium bg-feedback-success-pale text-feedback-success-deep flex items-center justify-center">
                            <Banknote className="w-5 h-5" />
                        </div>
                        <h3 className="text-neutral-muted text-xs font-semibold uppercase tracking-wider mt-4">
                            {t('Clearance Collections')}
                        </h3>
                        <p className="text-3xl font-extrabold text-neutral-primary mt-1">
                            ₱{summary?.document_requests?.total_revenue !== undefined
                                ? summary.document_requests.total_revenue.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                : '0.00'}
                        </p>
                    </div>
                </div>
            </>
        )}
    </div>
    );
};
