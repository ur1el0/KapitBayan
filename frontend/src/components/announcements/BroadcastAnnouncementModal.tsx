import React, { useId } from 'react';
import { Megaphone, Upload, X } from 'lucide-react';
import { useModalFocus } from '../../hooks/useModalFocus';

export interface BroadcastAnnouncementModalProps {
    mode?: 'create' | 'edit';
    onClose: () => void;
    onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
    title: string;
    setTitle: (val: string) => void;
    content: string;
    setContent: (val: string) => void;
    isPinned: boolean;
    setIsPinned: (val: boolean) => void;
    imagePreview: string | null;
    existingImageUrl?: string | null;
    onImageChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onRemoveImage: () => void;
    isSubmitting: boolean;
}

export const BroadcastAnnouncementModal: React.FC<BroadcastAnnouncementModalProps> = ({
    mode = 'create',
    onClose,
    onSubmit,
    title,
    setTitle,
    content,
    setContent,
    isPinned,
    setIsPinned,
    imagePreview,
    existingImageUrl,
    onImageChange,
    onRemoveImage,
    isSubmitting,
}) => {
    const announcementDialogTitleId = useId();
    const announcementDialogRef = useModalFocus<HTMLDivElement>(true, onClose);
    const displayedImage = imagePreview || existingImageUrl || null;
    const isEditing = mode === 'edit';

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
            <div
                ref={announcementDialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby={announcementDialogTitleId}
                tabIndex={-1}
                className="bg-white rounded-2xl shadow-xl max-w-lg w-full overflow-hidden border border-slate-100"
            >
                <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                    <h3 id={announcementDialogTitleId} className="text-base font-bold text-slate-900 flex items-center gap-2">
                        <Megaphone className="w-5 h-5 text-primary-text" />
                        {isEditing ? 'Edit Announcement' : 'Broadcast Announcement'}
                    </h3>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label={isEditing ? 'Close edit announcement dialog' : 'Close broadcast announcement dialog'}
                        className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] text-slate-400 hover:text-slate-600 transition-colors rounded-lg hover:bg-slate-200 cursor-pointer"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={onSubmit} className="p-6 space-y-4 bg-white">
                    <div>
                        <label htmlFor="announcement-title" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">Headline</label>
                        <input
                            id="announcement-title"
                            type="text"
                            required
                            value={title}
                            onChange={e => setTitle(e.target.value)}
                            placeholder="e.g., Scheduled Power Interruption"
                            className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 focus:border-primary focus:ring-2 focus:ring-primary/20 rounded-xl text-sm outline-none transition-all"
                        />
                    </div>

                    <div>
                        <label htmlFor="announcement-content" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">Full Content</label>
                        <textarea
                            id="announcement-content"
                            required
                            rows={4}
                            value={content}
                            onChange={e => setContent(e.target.value)}
                            placeholder="Write the full details of the announcement here..."
                            className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 focus:border-primary focus:ring-2 focus:ring-primary/20 rounded-xl text-sm outline-none transition-all resize-none"
                        />
                    </div>

                    {/* Image Upload Area */}
                    <div>
                        <span className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">Attached Image / Banner (Optional)</span>
                        {displayedImage ? (
                            <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-100 max-h-48 group">
                                <img src={displayedImage} alt="Announcement banner preview" className="w-full h-40 object-cover" />
                                {imagePreview ? (
                                    <button
                                        type="button"
                                        onClick={onRemoveImage}
                                        className="absolute top-2 right-2 p-1.5 bg-slate-900/70 hover:bg-rose-600 text-white rounded-lg transition-colors shadow-sm cursor-pointer"
                                        title="Remove image"
                                        aria-label="Remove attached image"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                ) : (
                                    <label
                                        htmlFor="announcement-image"
                                        className="absolute bottom-2 right-2 rounded-lg bg-white/95 px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm cursor-pointer hover:bg-white"
                                    >
                                        Replace image
                                    </label>
                                )}
                            </div>
                        ) : null}
                        {!displayedImage && (
                            <label
                                htmlFor="announcement-image"
                                className="flex flex-col items-center justify-center border-2 border-dashed border-slate-200 hover:border-primary rounded-xl p-4 bg-slate-50 hover:bg-primary/5 cursor-pointer transition-all focus-within:outline-none focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2"
                            >
                                <Upload className="w-5 h-5 text-slate-400 mb-1" aria-hidden="true" />
                                <span className="text-xs font-semibold text-slate-700">Click to upload banner or photo</span>
                                <span className="text-[11px] text-slate-400">PNG, JPG, or WEBP up to 5MB</span>
                                <input
                                    id="announcement-image"
                                    type="file"
                                    accept="image/*"
                                    aria-label="Upload announcement banner or photo"
                                    onChange={onImageChange}
                                    className="sr-only"
                                />
                            </label>
                        )}
                        {displayedImage && !imagePreview && (
                            <input
                                id="announcement-image"
                                type="file"
                                accept="image/*"
                                aria-label="Replace announcement banner or photo"
                                onChange={onImageChange}
                                className="sr-only"
                            />
                        )}
                    </div>

                    <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
                        <div className="flex items-center h-5">
                            <input
                                id="is_pinned"
                                type="checkbox"
                                checked={isPinned}
                                onChange={e => setIsPinned(e.target.checked)}
                                className="h-4 w-4 text-primary-text focus:ring-primary border-slate-300 rounded cursor-pointer"
                            />
                        </div>
                        <div className="flex flex-col">
                            <label htmlFor="is_pinned" className="text-xs font-bold text-slate-900 cursor-pointer">Pin to top</label>
                            <span className="text-[11px] text-slate-500">Pinned broadcasts will always appear first.</span>
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                        <button type="button" onClick={onClose} className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer">
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="px-5 py-2 rounded-xl text-sm font-semibold text-primary-foreground bg-primary hover:bg-primary-hover transition-colors disabled:opacity-70 disabled:cursor-not-allowed flex items-center gap-2 shadow-xs cursor-pointer"
                        >
                            {isSubmitting ? (
                                <><div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div> {isEditing ? 'Saving...' : 'Broadcasting...'}</>
                            ) : isEditing ? 'Save Changes' : 'Broadcast Now'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
