import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CircleHelp, Loader2, Search, ShieldCheck, BookOpen, Phone, PhoneCall } from 'lucide-react';
import { axiosPrivate } from '../../api/axios';
import { Link } from 'react-router-dom';

type ResidentFAQ = {
    id: number;
    question: string;
    answer: string;
    order: number;
    audience: 'RESIDENT' | 'STAFF';
    category: string;
};

type ResidentHotline = {
    id: number;
    name: string;
    number: string;
    category: string;
    category_display: string;
    is_active: boolean;
};

const CATEGORY_LABELS: Record<string, string> = {
    GETTING_STARTED: 'Getting started',
    ACCOUNT: 'Account access',
    DOCUMENTS: 'Documents',
    PAYMENTS: 'Fees and payments',
    QUEUE: 'Queue and schedules',
    ASSISTANCE: 'Assistance and programs',
    COMMUNITY: 'Community notices',
    ACCESSIBILITY: 'Accessibility',
    PRIVACY: 'Privacy and safety',
    OTHER: 'Other',
};

function unwrapPayload<T>(payload: unknown): T[] {
    if (Array.isArray(payload)) return payload as T[];
    if (payload && typeof payload === 'object' && Array.isArray((payload as { results?: unknown }).results)) {
        return (payload as { results: T[] }).results;
    }
    return [];
}

const getCategoryBadge = (category: string) => {
    switch (category) {
        case 'POLICE': return 'bg-blue-100 text-blue-800 border-blue-200';
        case 'FIRE': return 'bg-orange-100 text-orange-800 border-orange-200';
        case 'MEDICAL': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
        case 'BARANGAY': return 'bg-indigo-100 text-indigo-800 border-indigo-200';
        default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
};

export const ResidentHelp: React.FC = () => {
    const [faqs, setFaqs] = useState<ResidentFAQ[]>([]);
    const [hotlines, setHotlines] = useState<ResidentHotline[]>([]);
    const [loadingFaqs, setLoadingFaqs] = useState(true);
    const [loadingHotlines, setLoadingHotlines] = useState(true);
    const [faqError, setFaqError] = useState(false);
    const [hotlineError, setHotlineError] = useState(false);
    const [query, setQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('ALL');
    const [retryKey, setRetryKey] = useState(0);

    const loadData = useCallback(async (signal: AbortSignal) => {
        setLoadingFaqs(true);
        setLoadingHotlines(true);
        setFaqError(false);
        setHotlineError(false);

        const fetchFaqs = axiosPrivate.get('/faqs/', { signal })
            .then((res) => {
                setFaqs(unwrapPayload<ResidentFAQ>(res.data).filter((faq) => faq.audience === 'RESIDENT'));
            })
            .catch(() => {
                if (!signal.aborted) {
                    setFaqError(true);
                    setFaqs([]);
                }
            })
            .finally(() => {
                if (!signal.aborted) setLoadingFaqs(false);
            });

        const fetchHotlines = axiosPrivate.get('/hotlines/', { signal })
            .then((res) => {
                setHotlines(unwrapPayload<ResidentHotline>(res.data));
            })
            .catch(() => {
                if (!signal.aborted) {
                    setHotlineError(true);
                    setHotlines([]);
                }
            })
            .finally(() => {
                if (!signal.aborted) setLoadingHotlines(false);
            });

        await Promise.allSettled([fetchFaqs, fetchHotlines]);
    }, []);

    useEffect(() => {
        const controller = new AbortController();
        void loadData(controller.signal);
        return () => controller.abort();
    }, [loadData, retryKey]);

    const categories = useMemo(() => [...new Set(faqs.map((faq) => faq.category))], [faqs]);
    const filteredFaqs = useMemo(() => {
        const normalizedQuery = query.trim().toLocaleLowerCase();
        return faqs.filter((faq) => {
            const matchesQuery = !normalizedQuery
                || `${faq.question} ${faq.answer}`.toLocaleLowerCase().includes(normalizedQuery);
            return matchesQuery && (selectedCategory === 'ALL' || faq.category === selectedCategory);
        });
    }, [faqs, query, selectedCategory]);

    return (
        <main className="mx-auto max-w-5xl space-y-7 pb-10">
            <header className="max-w-3xl">
                <p className="text-sm font-bold uppercase tracking-wide text-primary-text">Resident support</p>
                <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-slate-900">Help and frequently asked questions</h1>
                <p className="mt-3 text-base leading-7 text-slate-700">
                    Search for help with your account and Barangay services. Local requirements and programs can differ, so check current instructions from your Barangay.
                </p>
            </header>

            <section className="flex flex-col gap-4 rounded-2xl border border-blue-200 bg-blue-50 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
                <div className="flex items-start gap-3">
                    <BookOpen className="mt-1 h-6 w-6 shrink-0 text-blue-900" aria-hidden="true" />
                    <div>
                        <h2 className="text-lg font-bold text-blue-950">Need a step-by-step guide?</h2>
                        <p className="mt-1 text-base leading-6 text-blue-950">Open the simple tutorial for help finding services and using your account.</p>
                    </div>
                </div>
                <Link to="/portal/tutorial" className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-lg bg-primary px-4 font-semibold text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                    How to use KapitBayan
                </Link>
            </section>

            {/* Emergency Hotlines Directory */}
            <section aria-labelledby="hotlines-heading" className="space-y-4 rounded-2xl border border-rose-200 bg-rose-50/60 p-5 shadow-xs sm:p-6">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-rose-600 text-white shadow-xs">
                            <PhoneCall className="h-6 w-6" aria-hidden="true" />
                        </div>
                        <div>
                            <h2 id="hotlines-heading" className="text-xl font-bold tracking-tight text-slate-900">
                                Emergency Hotlines
                            </h2>
                            <p className="text-sm text-slate-600">
                                Official emergency and rescue contact numbers for your Barangay. Tap to dial directly.
                            </p>
                        </div>
                    </div>
                    <a
                        href="tel:911"
                        className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl bg-rose-700 px-4 text-xs font-bold text-white shadow-xs hover:bg-rose-800 transition-colors shrink-0"
                    >
                        <Phone className="h-3.5 w-3.5" aria-hidden="true" /> National Emergency: 911
                    </a>
                </div>

                {loadingHotlines ? (
                    <div role="status" className="flex min-h-24 items-center justify-center gap-2 text-sm text-slate-600">
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Loading emergency contacts…
                    </div>
                ) : hotlineError ? (
                    <div className="rounded-xl border border-rose-200 bg-white p-4 text-sm text-rose-800">
                        <p className="font-semibold">Barangay hotlines could not be loaded.</p>
                        <p className="mt-1 text-xs text-slate-600">For immediate life-threatening emergencies, dial <a href="tel:911" className="font-bold underline text-rose-700">911</a> nationwide.</p>
                    </div>
                ) : hotlines.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-rose-300 bg-white p-5 text-center">
                        <Phone className="mx-auto h-6 w-6 text-rose-400" aria-hidden="true" />
                        <p className="mt-2 text-sm font-semibold text-slate-800">No Barangay-specific hotlines published yet.</p>
                        <p className="mt-1 text-xs text-slate-600">
                            For urgent response, contact the Philippine National Police or dial <a href="tel:911" className="font-bold underline text-rose-700">911</a>.
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {hotlines.map((hotline) => (
                            <div
                                key={hotline.id}
                                className="flex flex-col justify-between rounded-xl border border-rose-100 bg-white p-4 shadow-2xs transition-shadow hover:shadow-xs"
                            >
                                <div>
                                    <div className="flex items-center justify-between gap-2">
                                        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${getCategoryBadge(hotline.category)}`}>
                                            {hotline.category_display || hotline.category}
                                        </span>
                                    </div>
                                    <h3 className="mt-2 font-bold text-slate-900 line-clamp-1">{hotline.name}</h3>
                                    <p className="mt-1 font-mono text-sm font-semibold text-slate-700">{hotline.number}</p>
                                </div>
                                <div className="mt-4 pt-2 border-t border-slate-100">
                                    <a
                                        href={`tel:${hotline.number}`}
                                        className="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg bg-rose-600 px-3 text-xs font-bold text-white shadow-xs hover:bg-rose-700 transition-colors focus-visible:outline-2 focus-visible:outline-rose-600"
                                        aria-label={`Call ${hotline.name} at ${hotline.number}`}
                                    >
                                        <PhoneCall className="h-3.5 w-3.5" aria-hidden="true" />
                                        <span>Call {hotline.number}</span>
                                    </a>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            <section aria-labelledby="faq-list-heading" className="space-y-5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
                <div>
                    <h2 id="faq-list-heading" className="text-xl font-bold text-slate-900">Find an answer</h2>
                    <label className="relative mt-3 block">
                        <span className="sr-only">Search help questions and answers</span>
                        <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-500" aria-hidden="true" />
                        <input
                            type="search"
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder="For example: request a document"
                            className="min-h-12 w-full rounded-xl border border-slate-300 py-2 pl-11 pr-3 text-base focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                        />
                    </label>
                </div>

                {!loadingFaqs && !faqError && categories.length > 0 && (
                    <div aria-label="FAQ categories" className="flex flex-wrap gap-2">
                        <button type="button" aria-pressed={selectedCategory === 'ALL'} onClick={() => setSelectedCategory('ALL')} className={`min-h-11 rounded-full border px-4 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary ${selectedCategory === 'ALL' ? 'border-primary bg-primary text-primary-foreground' : 'border-slate-300 bg-white text-slate-800'}`}>
                            All topics
                        </button>
                        {categories.map((category) => (
                            <button key={category} type="button" aria-pressed={selectedCategory === category} onClick={() => setSelectedCategory(category)} className={`min-h-11 rounded-full border px-4 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary ${selectedCategory === category ? 'border-primary bg-primary text-primary-foreground' : 'border-slate-300 bg-white text-slate-800'}`}>
                                {CATEGORY_LABELS[category] ?? 'Other'}
                            </button>
                        ))}
                    </div>
                )}

                {loadingFaqs ? (
                    <div role="status" className="flex min-h-40 items-center justify-center gap-3 text-slate-700">
                        <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> Loading help…
                    </div>
                ) : faqError ? (
                    <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-slate-900">
                        <p className="font-bold">Help could not be loaded.</p>
                        <p className="mt-1 leading-6">Check your internet connection and try again. If the problem continues, contact your Barangay through a verified channel.</p>
                        <button type="button" onClick={() => setRetryKey((key) => key + 1)} className="mt-4 min-h-11 rounded-lg bg-primary px-4 font-semibold text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">Try again</button>
                    </div>
                ) : filteredFaqs.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-300 p-7 text-center">
                        <CircleHelp className="mx-auto h-8 w-8 text-slate-500" aria-hidden="true" />
                        <p className="mt-3 font-semibold text-slate-900">{faqs.length ? 'No answers match your search.' : 'No FAQs are available yet.'}</p>
                        <p className="mt-1 text-sm leading-6 text-slate-700">For current local instructions, contact your Barangay office.</p>
                    </div>
                ) : (
                    <div className="divide-y divide-slate-200">
                        {filteredFaqs.map((faq) => (
                            <details key={faq.id} className="group py-2 first:pt-0 last:pb-0">
                                <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 rounded-lg px-3 py-3 text-left font-semibold leading-6 text-slate-900 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-primary [&::-webkit-details-marker]:hidden">
                                    <span>{faq.question}</span>
                                    <span aria-hidden="true" className="shrink-0 text-2xl font-normal text-primary group-open:rotate-45">+</span>
                                </summary>
                                <div className="whitespace-pre-line px-3 pb-4 pt-1 text-base leading-7 text-slate-700">{faq.answer}</div>
                            </details>
                        ))}
                    </div>
                )}
                {!loadingFaqs && !faqError && <p role="status" className="text-sm text-slate-600">Showing {filteredFaqs.length} answers.</p>}
            </section>

            <aside className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-5 text-sm leading-6 text-slate-700">
                <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                <p>Do not share your password, OTP, or identity documents in personal messages. Barangay-specific eligibility, fees, required documents, and office hours must be confirmed with the responsible Barangay.</p>
            </aside>
        </main>
    );
};
