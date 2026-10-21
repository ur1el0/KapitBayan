import React from 'react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';
import type { NamedCount } from './types';
import { useLanguage } from '../../context/language-context';

interface ScenarioBreakdownChartProps {
    loading: boolean;
    data: NamedCount[];
}

const ChartSkeleton = ({ title }: { title?: string }) => (
    <div className="bg-surface rounded-large p-6 shadow-sm border border-border/80 animate-pulse">
        <div className="h-5 w-48 bg-border rounded mb-6">
            {title && <span className="sr-only">{title}</span>}
        </div>
        <div className="h-[250px] w-full bg-surface-subtle rounded-medium flex items-end justify-between px-4 pb-4">
            <div className="w-12 h-[60%] bg-border rounded-t-sm"></div>
            <div className="w-12 h-[80%] bg-border rounded-t-sm"></div>
            <div className="w-12 h-[40%] bg-border rounded-t-sm"></div>
            <div className="w-12 h-[100%] bg-border rounded-t-sm"></div>
            <div className="w-12 h-[30%] bg-border rounded-t-sm"></div>
        </div>
    </div>
);

export const ScenarioBreakdownChart: React.FC<ScenarioBreakdownChartProps> = ({
    loading,
    data,
}) => {
    const { t } = useLanguage();

    return loading ? (
        <ChartSkeleton title={t('Local Incident Scenarios')} />
    ) : (
        <div className="bg-surface rounded-large p-6 shadow-xs border border-border/80 hover:-translate-y-1 hover:shadow-md transition-all duration-300">
            <h2 className="text-base font-bold text-neutral-primary mb-6">{t('Local Incident Scenarios')}</h2>
            <div className="h-[250px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--kapitbayan-color-border)" />
                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--kapitbayan-color-text-muted)' }} />
                        <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--kapitbayan-color-text-muted)' }} />
                        <Tooltip cursor={{ fill: 'rgba(239,68,68,0.05)' }} />
                        <Bar dataKey="count" fill="var(--kapitbayan-color-danger)" radius={[4, 4, 0, 0]} maxBarSize={40} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
