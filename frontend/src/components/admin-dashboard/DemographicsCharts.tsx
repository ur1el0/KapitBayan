import React from 'react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';
import type { NamedCount, NamedValue } from './types';
import { useLanguage } from '../../context/language-context';

interface DemographicsChartsProps {
    purokData: NamedValue[];
    ageData: NamedCount[];
}

const COLORS = ['var(--brand-primary)', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

export const DemographicsCharts: React.FC<DemographicsChartsProps> = ({
    purokData,
    ageData,
}) => {
    const { t } = useLanguage();

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-surface rounded-large p-6 shadow-xs border border-border/80">
            <h2 className="text-base font-bold text-neutral-primary mb-6">{t('Purok Distribution')}</h2>
            <div className="h-[250px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={purokData}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={90}
                            paddingAngle={5}
                            dataKey="value"
                        >
                            {purokData.map((_, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip cursor={{ fill: 'transparent' }} />
                    </PieChart>
                </ResponsiveContainer>
            </div>
        </div>

        <div className="bg-surface rounded-large p-6 shadow-xs border border-border/80">
            <h2 className="text-base font-bold text-neutral-primary mb-6">{t('Age Demographics')}</h2>
            <div className="h-[250px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={ageData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--kapitbayan-color-border)" />
                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--kapitbayan-color-text-muted)' }} />
                        <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--kapitbayan-color-text-muted)' }} />
                        <Tooltip cursor={{ fill: 'rgba(0,71,186,0.05)' }} />
                        <Bar dataKey="count" fill="var(--brand-primary)" radius={[4, 4, 0, 0]} maxBarSize={40} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
        </div>
    );
};
