import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpen, CircleHelp, Loader2, Plus, Search, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { axiosPrivate } from '../../api/axios';

type FAQAudience = 'RESIDENT' | 'STAFF';

type FAQItem = {
    id: number;
    question: string;
    answer: string;
    order: number;
    audience: FAQAudience;
    category: string;
    is_published: boolean;
    barangay_id: number | null;
    barangay_name: string | null;
    scope: 'GLOBAL' | 'BARANGAY';
};

type FAQForm = {
    question: string;
    answer: string;
    order: string;
    category: string;
    is_published: boolean;
};

const CATEGORIES = [
    ['GETTING_STARTED', 'Getting started'],
    ['ACCOUNT', 'Account access'],
    ['DOCUMENTS', 'Documents and clearances'],
    ['PAYMENTS', 'Fees and payments'],
    ['QUEUE', 'Queue and schedules'],
    ['ASSISTANCE', 'Assistance and programs'],
    ['COMMUNITY', 'Community notices'],
    ['ACCESSIBILITY', 'Accessibility and older adults'],
    ['PRIVACY', 'Privacy and safety'],
    ['OTHER', 'Other'],
] as const;

const emptyForm = (): FAQForm => ({
    question: '',
    answer: '',
    order: '0',
    category: 'GETTING_STARTED',
    is_published: false,
});

function unwrapFaqs(payload: unknown): FAQItem[] {
    if (Array.isArray(payload)) return payload as FAQItem[];
    if (payload && typeof payload === 'object' && Array.isArray((payload as { results?: unknown }).results)) {
        return (payload as { results: FAQItem[] }).results;
    }
    return [];
}

export const Faqs: React.FC = () => {
    const [faqs, setFaqs] = useState<FAQItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [query, setQuery] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('ALL');
    const [publicationFilter, setPublicationFilter] = useState('ALL');
    const [editorOpen, setEditorOpen] = useState(false);
    const [editingFaq, setEditingFaq] = useState<FAQItem | null>(null);
    const [form, setForm] = useState<FAQForm>(() => emptyForm());
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');

    const loadFaqs = useCallback(async (signal?: AbortSignal) => {
        setLoading(true);
        setLoadError(false);
        try {
            const response = await axiosPrivate.get('/faqs/', { signal });
            setFaqs(unwrapFaqs(response.data));
        } catch {
            if (!signal?.aborted) {
                setLoadError(true);
                setFaqs([]);
            }
        } finally {
            if (!signal?.aborted) setLoading(false);
        }
    }, []);

    useEffect(() => {
        const controller = new AbortController();
        void loadFaqs(controller.signal);
        return () => controller.abort();
    }, [loadFaqs]);

    const filteredFaqs = useMemo(() => {
        const normalizedQuery = query.trim().toLocaleLowerCase();
        return faqs.filter((faq) => {
            const matchesQuery = !normalizedQuery
                || `${faq.question} ${faq.answer}`.toLocaleLowerCase().includes(normalizedQuery);
            const matchesCategory = categoryFilter === 'ALL' || faq.category === categoryFilter;
            const matchesPublication = publicationFilter === 'ALL'
                || (publicationFilter === 'PUBLISHED' ? faq.is_published : !faq.is_published);
            return matchesQuery && matchesCategory && matchesPublication;
        });
    }, [faqs, query, categoryFilter, publicationFilter]);

    const openCreateForm = () => {
        setEditingFaq(null);
        setForm(emptyForm());
        setEditorOpen(true);
        setMessage('');
    };

    const openEditForm = (faq: FAQItem) => {
        setEditingFaq(faq);
        setForm({
            question: faq.question,
            answer: faq.answer,
            order: String(faq.order),
            category: faq.category,
            is_published: faq.is_published,
        });
        setEditorOpen(true);
        setMessage('');
    };

    const saveFaq = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setSaving(true);
        setMessage('');
        const payload = {
            question: form.question.trim(),
            answer: form.answer.trim(),
            order: Number.parseInt(form.order, 10) || 0,
            audience: 'RESIDENT',
            category: form.category,
            is_published: form.is_published,
        };
        try {
            if (editingFaq) {
                await axiosPrivate.patch(`/faqs/${editingFaq.id}/`, payload);
                toast.success('FAQ updated.');
            } else {
                await axiosPrivate.post('/faqs/', payload);
                toast.success('FAQ created.');
            }
            setEditorOpen(false);
            setMessage('FAQ saved.');
            await loadFaqs();
        } catch {
            setMessage('We could not save this FAQ. Check your connection and try again.');
        } finally {
            setSaving(false);
        }
    };

    const togglePublished = async (faq: FAQItem) => {
        try {
            await axiosPrivate.patch(`/faqs/${faq.id}/`, { is_published: !faq.is_published });
            toast.success(faq.is_published ? 'FAQ unpublished.' : 'FAQ published.');
            await loadFaqs();
        } catch {
            toast.error('We could not update the FAQ. Please try again.');
        }
    };

    const deleteFaq = async (faq: FAQItem) => {
        if (!window.confirm(`Delete “${faq.question}”? This cannot be undone.`)) return;
        try {
            await axiosPrivate.delete(`/faqs/${faq.id}/`);
            toast.success('FAQ deleted.');
            await loadFaqs();
        } catch {
            toast.error('We could not delete the FAQ. Please try again.');
        }
    };

    const canManage = (faq: FAQItem) => faq.scope === 'BARANGAY' && faq.audience === 'RESIDENT';

    return (
        <main className="mx-auto max-w-5xl space-y-6 pb-12">
            <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                    <p className="text-sm font-semibold uppercase tracking-wide text-primary-text">Staff workspace</p>
                    <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">FAQ management</h1>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                        Publish clear, current answers for residents. Keep local eligibility, fees, required documents, and office hours verified by the responsible Barangay.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={openCreateForm}
                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 font-semibold text-primary-foreground outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                >
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    New resident FAQ
                </button>
            </header>

            {message && <p role="status" className="text-sm font-medium text-emerald-800">{message}</p>}

            {editorOpen && (
                <section aria-labelledby="faq-editor-heading" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                    <div className="mb-5 flex items-start justify-between gap-4">
                        <div>
                            <h2 id="faq-editor-heading" className="text-xl font-bold text-slate-900">
                                {editingFaq ? 'Edit FAQ' : 'Create FAQ'}
                            </h2>
                            <p className="mt-1 text-sm text-slate-600">
                                This FAQ will be visible to residents in your Barangay only.
                            </p>
                        </div>
                        <button type="button" onClick={() => setEditorOpen(false)} className="min-h-11 rounded-lg px-3 font-semibold text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
                            Cancel
                        </button>
                    </div>
                    <form className="grid gap-4 md:grid-cols-2" onSubmit={saveFaq}>
                        <label className="grid gap-1.5 text-sm font-semibold text-slate-800 md:col-span-2">
                            Question
                            <input required maxLength={255} value={form.question} onChange={(event) => setForm((old) => ({ ...old, question: event.target.value }))} className="min-h-11 rounded-lg border border-slate-300 px-3 font-normal focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary" />
                        </label>
                        <label className="grid gap-1.5 text-sm font-semibold text-slate-800 md:col-span-2">
                            Answer
                            <textarea required rows={5} value={form.answer} onChange={(event) => setForm((old) => ({ ...old, answer: event.target.value }))} className="min-h-32 rounded-lg border border-slate-300 px-3 py-2 font-normal leading-6 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary" />
                        </label>
                        <label className="grid gap-1.5 text-sm font-semibold text-slate-800">
                            Category
                            <select value={form.category} onChange={(event) => setForm((old) => ({ ...old, category: event.target.value }))} className="min-h-11 rounded-lg border border-slate-300 bg-white px-3 font-normal focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
                                {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                            </select>
                        </label>
                        <label className="grid gap-1.5 text-sm font-semibold text-slate-800">
                            Display order
                            <input type="number" value={form.order} onChange={(event) => setForm((old) => ({ ...old, order: event.target.value }))} className="min-h-11 rounded-lg border border-slate-300 px-3 font-normal focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary" />
                        </label>
                        <label className="flex min-h-11 items-center gap-3 self-end rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-800">
                            <input type="checkbox" checked={form.is_published} onChange={(event) => setForm((old) => ({ ...old, is_published: event.target.checked }))} className="h-5 w-5 accent-blue-800" />
                            Publish for residents in this Barangay
                        </label>
                        <div className="flex flex-wrap items-center gap-3 md:col-span-2">
                            <button type="submit" disabled={saving} className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 font-semibold text-primary-foreground disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
                                {saving ? 'Saving…' : 'Save FAQ'}
                            </button>
                            <p role="status" className="text-sm text-rose-700">{message.includes('could not save') ? message : ''}</p>
                        </div>
                    </form>
                </section>
            )}

            <section aria-label="FAQ list" className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <label className="relative sm:col-span-2">
                        <span className="sr-only">Search FAQs</span>
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
                        <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search questions and answers" className="min-h-11 w-full rounded-lg border border-slate-300 pl-9 pr-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary" />
                    </label>
                    <label className="grid gap-1 text-sm font-medium text-slate-700">
                        <span className="sr-only">Filter by category</span>
                        <select aria-label="Filter by category" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} className="min-h-11 rounded-lg border border-slate-300 bg-white px-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
                            <option value="ALL">All categories</option>
                            {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                        </select>
                    </label>
                    <label className="grid gap-1 text-sm font-medium text-slate-700">
                        <span className="sr-only">Filter by status</span>
                        <select aria-label="Filter by status" value={publicationFilter} onChange={(event) => setPublicationFilter(event.target.value)} className="min-h-11 rounded-lg border border-slate-300 bg-white px-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
                            <option value="ALL">All statuses</option>
                            <option value="PUBLISHED">Published</option>
                            <option value="DRAFT">Draft</option>
                        </select>
                    </label>
                </div>

                {loading ? (
                    <div role="status" className="flex min-h-40 items-center justify-center gap-3 text-slate-600">
                        <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> Loading FAQs…
                    </div>
                ) : loadError ? (
                    <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-slate-800">
                        <p className="font-semibold">We could not load FAQs.</p>
                        <p className="mt-1 text-sm">Check your connection and retry. No sample guidance is shown when the service is unavailable.</p>
                        <button type="button" onClick={() => void loadFaqs()} className="mt-3 min-h-11 rounded-lg bg-primary px-4 font-semibold text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">Try again</button>
                    </div>
                ) : filteredFaqs.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center">
                        <CircleHelp className="mx-auto h-8 w-8 text-slate-500" aria-hidden="true" />
                        <p className="mt-3 font-semibold text-slate-800">{faqs.length ? 'No FAQs match these filters.' : 'No FAQs are available to manage yet.'}</p>
                        <p className="mt-1 text-sm text-slate-600">Create a reviewed answer or change your search filters.</p>
                    </div>
                ) : (
                    <ul className="divide-y divide-slate-200" aria-live="polite">
                        {filteredFaqs.map((faq) => (
                            <li key={faq.id} className="py-4 first:pt-1 last:pb-1">
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                    <div className="min-w-0">
                                        <p className="font-semibold leading-6 text-slate-900">{faq.question}</p>
                                        <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">{faq.answer}</p>
                                        <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                                            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-800">{CATEGORIES.find(([value]) => value === faq.category)?.[1] ?? 'Other'}</span>
                                            <span className="rounded-full bg-blue-50 px-2.5 py-1 text-blue-900">Residents</span>
                                            <span className="rounded-full bg-violet-50 px-2.5 py-1 text-violet-900">{faq.barangay_name || 'This Barangay'}</span>
                                            <span className={`rounded-full px-2.5 py-1 ${faq.is_published ? 'bg-emerald-50 text-emerald-900' : 'bg-amber-50 text-amber-950'}`}>{faq.is_published ? 'Published' : 'Draft'}</span>
                                        </div>
                                    </div>
                                    {canManage(faq) && (
                                        <div className="flex shrink-0 flex-wrap gap-2">
                                            <button type="button" onClick={() => openEditForm(faq)} className="min-h-11 rounded-lg border border-slate-300 px-3 font-semibold text-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">Edit</button>
                                            <button type="button" onClick={() => void togglePublished(faq)} className="min-h-11 rounded-lg border border-slate-300 px-3 font-semibold text-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">{faq.is_published ? 'Unpublish' : 'Publish'}</button>
                                            <button type="button" onClick={() => void deleteFaq(faq)} aria-label={`Delete FAQ: ${faq.question}`} className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-rose-300 px-3 font-semibold text-rose-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-700">
                                                <Trash2 className="h-4 w-4" aria-hidden="true" /> Delete
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
                {!loading && !loadError && <p role="status" className="text-sm text-slate-600">Showing {filteredFaqs.length} of {faqs.length} FAQs.</p>}
            </section>

            <aside className="rounded-2xl border border-blue-200 bg-blue-50 p-5 text-sm leading-6 text-blue-950">
                <BookOpen className="mb-2 h-5 w-5" aria-hidden="true" />
                Use plain language and steps residents can follow. Confirm local eligibility, fees, documents, office hours, and emergency contacts with the responsible Barangay before publishing.
            </aside>
        </main>
    );
};
