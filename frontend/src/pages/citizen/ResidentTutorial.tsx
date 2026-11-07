import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, BookOpen, FileText, ListOrdered, Radio, ShieldCheck, Users } from 'lucide-react';
import { useLanguage } from '../../context/language-context';

const steps = [
    {
        title: 'Start at your Dashboard',
        description: 'After signing in, use the menu or service cards to choose what you need. You can return to the Dashboard whenever you want.',
        icon: <BookOpen className="h-6 w-6" aria-hidden="true" />,
    },
    {
        title: 'Request a document',
        description: 'Open Documents, choose the service you need, and follow the instructions on the screen. Review your information before sending. Return to Documents later to check the request status.',
        icon: <FileText className="h-6 w-6" aria-hidden="true" />,
    },
    {
        title: 'Check the queue and schedule',
        description: 'Open Queue to see available queue information. If your Barangay has posted an appointment or activity schedule, check its date, time, and location before going.',
        icon: <ListOrdered className="h-6 w-6" aria-hidden="true" />,
    },
    {
        title: 'Read community updates',
        description: 'Open the Community Bulletin to read announcements. Check the date and details, and confirm urgent information with your Barangay through a verified contact.',
        icon: <Radio className="h-6 w-6" aria-hidden="true" />,
    },
    {
        title: 'Find help',
        description: 'Use Assistance or Report Issue when you need those services. Follow the instructions shown and check the service page for updates. Local requirements and availability can differ.',
        icon: <Users className="h-6 w-6" aria-hidden="true" />,
    },
];

export const ResidentTutorial: React.FC = () => {
    const isPortalPage = useLocation().pathname === '/portal/tutorial';
    const { t } = useLanguage();

    return (
    <main className="mx-auto max-w-4xl space-y-6 pb-10">
        {isPortalPage && (
            <Link
                to="/portal/documents"
                className="inline-flex min-h-11 items-center gap-2 rounded-lg px-2 font-semibold text-primary underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            >
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                {t('Back to the resident portal')}
            </Link>
        )}
        <header className="rounded-2xl bg-primary p-6 text-primary-foreground sm:p-8">
            <p className="text-sm font-bold uppercase tracking-wide opacity-90">{t('Resident guide')}</p>
            <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">{t('How to use KapitBayan')}</h1>
            <p className="mt-3 max-w-2xl text-base leading-7 opacity-95">
                {t('Take one step at a time. You can come back to this guide whenever you need it. Button names may vary a little between the website and the mobile app.')}
            </p>
        </header>

        {!isPortalPage && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
                <h2 className="text-xl font-bold text-slate-900">{t('First time here?')}</h2>
                <div className="mt-2 space-y-2 text-base leading-7 text-slate-700">
                    <p>{t('On the sign-in screen, choose Register as Resident and follow the steps.')}</p>
                    <p>{t('If your account needs review, wait or contact your Barangay. Do not make another account.')}</p>
                    <p>{t('Already have an account? Sign in and open your Dashboard.')}</p>
                </div>
            </section>
        )}

        <ol className="space-y-3">
            {steps.map((step) => (
                <li key={step.title} className="flex items-start gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                    <span className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-primary">
                        {step.icon}
                    </span>
                    <div>
                        <h2 className="text-lg font-bold leading-7 text-slate-900">{t(step.title)}</h2>
                        <p className="mt-1 text-base leading-7 text-slate-700">{t(step.description)}</p>
                    </div>
                </li>
            ))}
        </ol>

        <section aria-labelledby="tutorial-accessibility" className="rounded-2xl border border-blue-200 bg-blue-50 p-5 sm:p-6">
            <h2 id="tutorial-accessibility" className="text-xl font-bold text-blue-950">{t('Make the app easier to use')}</h2>
            <ul className="mt-3 list-disc space-y-2 pl-6 text-base leading-7 text-blue-950">
                <li>{t("To make text larger, change the text size in your phone's settings. On the website, zoom in using your browser.")}</li>
                <li>{t('If you use a screen reader, turn on TalkBack in Android Accessibility settings.')}</li>
                <li>{t('Someone you trust can help. Keep control of your phone. Do not share your password or the code sent to you (OTP).')}</li>
                <li>{t('If a page does not load, check your internet. Check your request history before sending it again.')}</li>
            </ul>
        </section>

        <aside className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-5 text-base leading-7 text-slate-700">
            <ShieldCheck className="mt-1 h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
            <p>{t('Keep your password and ID documents private. Do not share the code sent to you (OTP). Ask your Barangay about requirements, fees, papers to bring, and office hours.')}</p>
        </aside>

        <div className="flex flex-wrap gap-3">
            {isPortalPage ? (
                <Link to="/portal/help" className="inline-flex min-h-12 items-center justify-center rounded-xl bg-primary px-5 font-semibold text-primary-foreground hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                    {t('Open resident FAQs')}
                </Link>
            ) : (
                <>
                    <Link to="/login" className="inline-flex min-h-12 items-center justify-center rounded-xl bg-primary px-5 font-semibold text-primary-foreground hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                        {t('Sign in')}
                    </Link>
                    <Link to="/register" className="inline-flex min-h-12 items-center justify-center rounded-xl border border-slate-300 bg-white px-5 font-semibold text-slate-900 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                        {t('Register as a resident')}
                    </Link>
                </>
            )}
        </div>
    </main>
    );
};
