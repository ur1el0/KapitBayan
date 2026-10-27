import toast from 'react-hot-toast';
import React, { useEffect, useState } from 'react';
import { axiosPrivate } from '../../api/axios';
import { Pin, Megaphone, Plus, Trash, Share2, Pencil } from 'lucide-react';
import { useAuth } from '../../context/auth-context';
import { BroadcastAnnouncementModal } from '../../components/announcements/BroadcastAnnouncementModal';
import { AnnouncementShareKitModal } from '../../components/announcements/AnnouncementShareKitModal';
import { InlineErrorState } from '../../components/ui/InlineErrorState';

interface Announcement {
    id: number;
    title: string;
    content: string;
    image?: string | null;
    is_pinned: boolean;
    created_at: string;
}

const CardSkeleton = () => (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm animate-pulse flex flex-col h-[200px]">
        <div className="p-5 flex-1">
            <div className="flex justify-between items-start mb-4">
                <div className="w-10 h-10 bg-slate-200 rounded-lg"></div>
                <div className="w-16 h-5 bg-slate-200 rounded-full"></div>
            </div>
            <div className="h-5 w-3/4 bg-slate-200 rounded mb-3"></div>
            <div className="h-4 w-full bg-slate-100 rounded mb-2"></div>
            <div className="h-4 w-2/3 bg-slate-100 rounded"></div>
        </div>
    </div>
);

export const Announcements: React.FC = () => {
    const { user } = useAuth();
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState('');
    const [retrying, setRetrying] = useState(false);

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingAnnouncement, setEditingAnnouncement] = useState<Announcement | null>(null);
    const [shareAnnouncement, setShareAnnouncement] = useState<Announcement | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [title, setTitle] = useState('');
    const [content, setContent] = useState('');
    const [isPinned, setIsPinned] = useState(false);
    const [imageFile, setImageFile] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);

    const fetchAnnouncements = async (isRetry = false) => {
        if (isRetry) {
            setRetrying(true);
        } else {
            setLoading(true);
        }

        try {
            const response = await axiosPrivate.get('/announcements/');
            setAnnouncements(response.data.results || response.data);
            setError('');
        } catch (err) {
            setError('Failed to load announcements.');
            console.error(err);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!window.confirm("Are you sure you want to permanently delete this announcement?")) return;
        try {
            await axiosPrivate.delete(`/announcements/${id}/`);
            setAnnouncements(prev => prev.filter(a => a.id !== id));
            toast.success('Announcement deleted.');
        } catch (err) {
            console.error("Failed to delete announcement", err);
            toast.error('Failed to delete announcement.');
        }
    };

    const handleShare = (announcement: Announcement) => {
        const barangayId = user?.barangay?.id ?? user?.barangay_id;
        if (!barangayId) {
            toast.error('Your account is not linked to a barangay.');
            return;
        }
        setShareAnnouncement(announcement);
    };

    const openCreateModal = () => {
        setEditingAnnouncement(null);
        setTitle('');
        setContent('');
        setIsPinned(false);
        handleRemoveImage();
        setIsModalOpen(true);
    };

    const handleEdit = (announcement: Announcement) => {
        setEditingAnnouncement(announcement);
        setTitle(announcement.title);
        setContent(announcement.content);
        setIsPinned(announcement.is_pinned);
        handleRemoveImage();
        setIsModalOpen(true);
    };

    useEffect(() => {
        fetchAnnouncements();
    }, []);

    const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                toast.error('Please upload a valid image file (PNG, JPG, WebP).');
                return;
            }
            if (file.size > 5 * 1024 * 1024) {
                toast.error('Image size cannot exceed 5MB.');
                return;
            }
            setImageFile(file);
            setImagePreview(URL.createObjectURL(file));
        }
    };

    const handleRemoveImage = () => {
        setImageFile(null);
        if (imagePreview) {
            URL.revokeObjectURL(imagePreview);
            setImagePreview(null);
        }
    };

    const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            const formData = new FormData();
            formData.append('title', title.trim());
            formData.append('content', content.trim());
            formData.append('is_pinned', String(isPinned));
            if (imageFile) {
                formData.append('image', imageFile);
            }

            if (editingAnnouncement) {
                await axiosPrivate.patch(`/announcements/${editingAnnouncement.id}/`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                toast.success('Announcement updated successfully.');
            } else {
                await axiosPrivate.post('/announcements/', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                toast.success('Announcement broadcasted successfully!');
            }
            await fetchAnnouncements();
            closeModal();
        } catch (err) {
            console.error('Failed to save announcement.', err);
            toast.error(editingAnnouncement ? 'Failed to update announcement.' : 'Failed to create announcement.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setEditingAnnouncement(null);
        setTitle('');
        setContent('');
        setIsPinned(false);
        handleRemoveImage();
    };

    if (loading && announcements.length === 0) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-4">
                {[1, 2, 3, 4, 5, 6].map(i => <CardSkeleton key={i} />)}
            </div>
        );
    }
    
    return (
        <div className="space-y-6 relative animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header Row */}
            <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-2xs border border-slate-100">
                <div className="flex min-w-0 items-start gap-2 text-slate-700">
                    <Megaphone className="mt-0.5 h-5 w-5 shrink-0 text-primary-text" />
                    <div>
                        <span className="font-semibold text-sm">Active Broadcasts</span>
                        <p className="mt-1 max-w-2xl text-xs font-normal text-slate-500">
                            KapitBayan cannot manage replies on external social pages. Apply that platform’s comment settings when posting and direct residents to complete requests in KapitBayan.
                        </p>
                    </div>
                </div>
                {user?.role === 'ADMIN' && (
                    <button
                        onClick={openCreateModal}
                        className="flex items-center gap-2 bg-primary hover:bg-primary-hover text-primary-foreground px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-sm hover:shadow active:scale-95 cursor-pointer"
                    >
                        <Plus className="w-4 h-4" />
                        New Announcement
                    </button>
                )}
            </div>
                    
            {/* Announcements Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {error && (
                    <div className="col-span-full">
                        <InlineErrorState
                            message="We couldn't load announcements."
                            onRetry={() => void fetchAnnouncements(true)}
                            retrying={retrying}
                        />
                    </div>
                )}
                {!error && announcements.length === 0 ? (
                    <div className="col-span-full py-12 text-center text-slate-500 bg-white rounded-xl border border-slate-100 border-dashed">
                        No announcements active right now.
                    </div>
                ) : (
                    announcements.map((ann) => (
                        <div key={ann.id} className="group bg-white rounded-2xl shadow-2xs border border-slate-100 overflow-hidden hover:shadow-md transition-all flex flex-col">
                            {/* Attached Banner Image if present */}
                            {ann.image && (
                                <div className="h-44 w-full overflow-hidden bg-slate-100 border-b border-slate-100 relative">
                                    <img 
                                        src={ann.image} 
                                        alt={ann.title} 
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" 
                                    />
                                </div>
                            )}

                            {/* Card Header */}
                            <div className={`px-5 py-3 border-b flex justify-between items-center ${ann.is_pinned ? 'bg-amber-50/70 border-amber-100' : 'bg-slate-50 border-slate-100'}`}>
                                <div className="flex items-center gap-2">
                                    {ann.is_pinned ? (
                                        <Pin className="w-4 h-4 text-amber-600 fill-amber-600" />
                                    ) : (
                                        <Megaphone className="w-4 h-4 text-slate-400" />
                                    )}
                                    <span className={`text-xs font-bold uppercase tracking-wider ${ann.is_pinned ? 'text-amber-800' : 'text-slate-500'}`}>
                                        {ann.is_pinned ? 'Pinned Broadcast' : 'Standard Broadcast'}
                                    </span>
                                </div>
                                <span className="text-xs text-slate-400 font-medium">
                                    {new Date(ann.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                                </span>
                            </div>

                            {/* Card Body */}
                            <div className="p-5 flex-1 flex flex-col justify-between">
                                <div>
                                    <h4 className="font-bold text-slate-900 text-base mb-2 group-hover:text-primary-text transition-colors leading-snug">
                                        {ann.title}
                                    </h4>
                                    <p className="text-sm text-slate-600 line-clamp-3 leading-relaxed">
                                        {ann.content}
                                    </p>
                                </div>

                                {user?.role === 'ADMIN' && (
                                    <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-end gap-2">
                                        <button
                                            onClick={() => handleShare(ann)}
                                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                                        >
                                            <Share2 className="h-3.5 w-3.5" /> Share announcement
                                        </button>
                                        <button
                                            onClick={() => handleEdit(ann)}
                                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                                            aria-label={`Edit ${ann.title}`}
                                        >
                                            <Pencil className="h-3.5 w-3.5" /> Edit
                                        </button>
                                        <button 
                                            onClick={() => handleDelete(ann.id)}
                                            className="text-slate-400 hover:text-rose-600 p-1.5 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer"
                                            title="Delete broadcast"
                                            aria-label={`Delete ${ann.title}`}
                                        >
                                            <Trash className="w-4 h-4" />
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Create Announcement Modal */}
            {isModalOpen && (
                <BroadcastAnnouncementModal
                    mode={editingAnnouncement ? 'edit' : 'create'}
                    onClose={closeModal}
                    onSubmit={handleSave}
                    title={title}
                    setTitle={setTitle}
                    content={content}
                    setContent={setContent}
                    isPinned={isPinned}
                    setIsPinned={setIsPinned}
                    imagePreview={imagePreview}
                    existingImageUrl={editingAnnouncement?.image}
                    onImageChange={handleImageChange}
                    onRemoveImage={handleRemoveImage}
                    isSubmitting={isSubmitting}
                />
            )}

            {shareAnnouncement && (
                <AnnouncementShareKitModal
                    announcement={shareAnnouncement}
                    barangayId={user?.barangay?.id ?? user?.barangay_id ?? ''}
                    onClose={() => setShareAnnouncement(null)}
                />
            )}
        </div>
    );
};
