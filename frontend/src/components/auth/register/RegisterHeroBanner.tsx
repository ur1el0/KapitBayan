import React from 'react';
import { Clock, FileCheck2, Users } from 'lucide-react';
import { useLanguage } from '../../../context/language-context';

export const RegisterHeroBanner: React.FC = () => {
    const { t } = useLanguage();
    return (
    <div className="relative flex w-full flex-col justify-between overflow-hidden bg-gradient-to-b from-[#0284C7] via-[#0369A1] to-[#075985] p-5 text-white md:min-h-screen md:w-5/12 md:p-8 lg:w-[40%] lg:p-14">
        <div className="pointer-events-none absolute inset-0 overflow-hidden opacity-10" aria-hidden="true">
            <svg className="h-full w-full" viewBox="0 0 500 800" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M-100 200 C 100 400, 300 100, 600 300 C 900 500, 700 800, 1000 700" stroke="white" strokeWidth="2" />
                <path d="M-50 400 C 150 600, 350 300, 650 500 C 950 700, 750 1000, 1050 900" stroke="white" strokeWidth="2" />
                <path d="M-150 0 C 50 200, 250 -100, 550 100 C 850 300, 650 600, 950 500" stroke="white" strokeWidth="2" />
            </svg>
        </div>

        <span className="relative z-10 text-lg font-bold tracking-tight sm:text-2xl">KapitBayan</span>

        <div className="relative z-10 mb-auto mt-10 hidden md:mt-14 md:block">
            <h1 className="mb-4 text-4xl font-extrabold leading-[1.15] tracking-tight text-white lg:text-[2.75rem]">
                {t('Resident')}<br />{t('Account')}<br />{t('Registration')}
            </h1>
            <p className="mb-10 max-w-sm text-sm font-normal leading-relaxed text-blue-100/75 lg:text-base">
                {t('Register your resident account to request clearances, access community services, and track queue updates from your Barangay.')}
            </p>
            <div className="space-y-4">
                <div className="flex items-center gap-3.5">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/10 text-white backdrop-blur-sm">
                        <FileCheck2 className="h-5 w-5 text-sky-200" aria-hidden="true" />
                    </div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-100/90 lg:text-xs">{t('Barangay services and clearances')}</span>
                </div>
                <div className="flex items-center gap-3.5">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/10 text-white backdrop-blur-sm">
                        <Clock className="h-5 w-5 text-sky-200" aria-hidden="true" />
                    </div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-100/90 lg:text-xs">{t('Queue updates')}</span>
                </div>
                <div className="flex items-center gap-3.5">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/10 text-white backdrop-blur-sm">
                        <Users className="h-5 w-5 text-sky-200" aria-hidden="true" />
                    </div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-100/90 lg:text-xs">{t('Community program updates')}</span>
                </div>
            </div>
        </div>
    </div>
    );
};
