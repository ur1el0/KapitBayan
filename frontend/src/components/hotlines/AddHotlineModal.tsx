import React, { useId } from 'react';
import { X } from 'lucide-react';
import { useModalFocus } from '../../hooks/useModalFocus';

export interface AddHotlineModalProps {
    mode?: 'create' | 'edit';
    onClose: () => void;
    onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
    form: {
        name: string;
        number: string;
        category: string;
        is_active: boolean;
    };
    setForm: React.Dispatch<React.SetStateAction<{
        name: string;
        number: string;
        category: string;
        is_active: boolean;
    }>>;
    categories: string[];
    isSubmitting: boolean;
}

export const AddHotlineModal: React.FC<AddHotlineModalProps> = ({
    mode = 'create',
    onClose,
    onSubmit,
    form,
    setForm,
    categories,
    isSubmitting,
}) => {
    const hotlineDialogTitleId = useId();
    const hotlineDialogRef = useModalFocus<HTMLDivElement>(true, onClose);
    const isEditing = mode === 'edit';

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60">
            <div
                ref={hotlineDialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby={hotlineDialogTitleId}
                tabIndex={-1}
                className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4"
            >
                <div className="flex items-center justify-between">
                    <h2 id={hotlineDialogTitleId} className="text-xl font-bold text-slate-900">{isEditing ? 'Edit Emergency Hotline' : 'Add Emergency Hotline'}</h2>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label={isEditing ? 'Close edit emergency hotline dialog' : 'Close add emergency hotline dialog'}
                        className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] text-slate-400 hover:text-slate-600 transition-colors rounded-lg hover:bg-slate-100 cursor-pointer"
                    >
                        <X size={20} />
                    </button>
                </div>
                <form onSubmit={onSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="hotline-name" className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                        <input
                            id="hotline-name"
                            required
                            value={form.name}
                            onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                            placeholder="e.g. Philippine National Police"
                            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                    </div>
                    <div>
                        <label htmlFor="hotline-number" className="block text-sm font-medium text-slate-700 mb-1">Number</label>
                        <input
                            id="hotline-number"
                            required
                            value={form.number}
                            onChange={e => setForm(p => ({ ...p, number: e.target.value }))}
                            placeholder="e.g. 117 or 0912-345-6789"
                            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                    </div>
                    <div>
                        <label htmlFor="hotline-category" className="block text-sm font-medium text-slate-700 mb-1">Category</label>
                        <select
                            id="hotline-category"
                            value={form.category}
                            onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
                            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                            {categories.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                    </div>
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                        <input
                            type="checkbox"
                            checked={form.is_active}
                            onChange={e => setForm(p => ({ ...p, is_active: e.target.checked }))}
                            className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary"
                        />
                        Active and visible to residents
                    </label>
                    <div className="flex justify-end gap-3 pt-2">
                        <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900 font-medium transition-colors">
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="px-4 py-2 bg-primary hover:bg-primary-hover text-primary-foreground text-sm font-medium rounded-md transition-colors disabled:opacity-60"
                        >
                            {isSubmitting ? (isEditing ? 'Saving...' : 'Adding...') : (isEditing ? 'Save Changes' : 'Add Hotline')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
