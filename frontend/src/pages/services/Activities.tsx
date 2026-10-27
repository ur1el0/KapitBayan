import toast from 'react-hot-toast';
import React, { useEffect, useState } from 'react';
import { axiosPrivate } from '../../api/axios';
import { InlineErrorState } from '../../components/ui/InlineErrorState';
import { Calendar, MapPin, Clock, Plus, Trash2, Pencil } from 'lucide-react';
import { ScheduleActivityModal } from '../../components/activities/ScheduleActivityModal';

interface Activity {
    id: number;
    title: string;
    description: string;
    location: string;
    event_datetime: string;
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

export const Activities: React.FC = () => {
    const [activities, setActivities] = useState<Activity[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [retrying, setRetrying] = useState(false);

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingActivity, setEditingActivity] = useState<Activity | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [location, setLocation] = useState('');
    const [eventDate, setEventDate] = useState('');

    const closeModal = () => {
        setIsModalOpen(false);
        setEditingActivity(null);
        setTitle('');
        setDescription('');
        setLocation('');
        setEventDate('');
    };

    const openCreateModal = () => {
        closeModal();
        setIsModalOpen(true);
    };

    const toDateTimeLocalValue = (value: string) => {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return '';
        date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
        return date.toISOString().slice(0, 16);
    };

    const handleEdit = (activity: Activity) => {
        setEditingActivity(activity);
        setTitle(activity.title);
        setDescription(activity.description);
        setLocation(activity.location);
        setEventDate(toDateTimeLocalValue(activity.event_datetime));
        setIsModalOpen(true);
    };
    const fetchActivities = async (isRetry = false) => {
        if (isRetry) {
            setRetrying(true);
        } else {
            setLoading(true);
        }

        try {
            const response = await axiosPrivate.get('/activities/');
            setActivities(response.data.results || response.data);
            setError('');
        } catch (err) {
            setError('Failed to load activities.');
            console.error(err);
        } finally {
            setLoading(false);
            setRetrying(false);
        }
    };

    useEffect(() => {
        void fetchActivities();
    }, []);

    const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            const isoDate = new Date(eventDate).toISOString();
            const payload = {
                title,
                description,
                location,
                event_datetime: isoDate,
            };
            if (editingActivity) {
                await axiosPrivate.patch(`/activities/${editingActivity.id}/`, payload);
            } else {
                await axiosPrivate.post('/activities/', payload);
            }
            await fetchActivities();
            closeModal();
            toast.success(editingActivity ? 'Activity updated successfully.' : 'Activity scheduled successfully!');
        } catch (err) {
            console.error("Failed to save activity", err);
            toast.error(editingActivity ? 'Failed to update activity.' : 'Failed to schedule activity.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDelete = async (id: number, title: string) => {
        if (!window.confirm(`Are you sure you want to cancel and remove "${title}"?`)) {
            return;
        }
        try {
            await axiosPrivate.delete(`/activities/${id}/`);
            toast.success('Activity removed successfully.');
            setActivities(prev => prev.filter(act => act.id !== id));
        } catch (err) {
            console.error('Failed to delete activity', err);
            toast.error('Failed to remove activity.');
        }
    };
    if (loading && activities.length === 0) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-4">
                {[1, 2, 3, 4, 5, 6].map(i => <CardSkeleton key={i} />)}
            </div>
        );
    }
    
    return (
        <div className="space-y-6 relative animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header / Action Row */}
            <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-slate-100">
                <div className="flex items-center gap-2 text-slate-700">
                    <Calendar className="w-5 h-5 text-primary-text" />
                    <span className="font-semibold text-sm">Upcoming Schedules</span>
                </div>
                <button 
                    onClick={openCreateModal}
                    className="flex items-center gap-2 bg-primary hover:bg-primary-hover text-primary-foreground px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-sm hover:shadow active:scale-95"
                >
                    <Plus className="w-4 h-4" />
                    Schedule Activity
                </button>
            </div>

            {/* Activities Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {error && (
                    <div className="col-span-full">
                        <InlineErrorState
                            message="We couldn't load activities."
                            onRetry={() => void fetchActivities(true)}
                            retrying={retrying}
                        />
                    </div>
                )}
                {!error && activities.length === 0 ? (
                    <div className="col-span-full py-12 text-center text-slate-500 bg-white rounded-xl border border-slate-100 border-dashed">
                        No upcoming activities scheduled.
                    </div>
                ) : (
                    activities.map((act) => {
                        const eventDateObj = new Date(act.event_datetime);
                        return (
                            <div key={act.id} className="group bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-md transition-all flex flex-col sm:flex-row">
                                
                                {/* Date Highlight Box */}
                                <div className="bg-primary/10 border-r border-slate-100 p-5 flex flex-col items-center justify-center min-w-[100px] shrink-0 text-center">
                                    <span className="text-xs font-bold text-primary-text uppercase tracking-widest mb-1">
                                        {eventDateObj.toLocaleDateString(undefined, { month: 'short' })}
                                    </span>
                                    <span className="text-3xl font-black text-[#0f172a] leading-none mb-1">
                                        {eventDateObj.getDate()}
                                    </span>
                                    <span className="text-xs font-semibold text-slate-500">
                                        {eventDateObj.toLocaleDateString(undefined, { weekday: 'short' })}
                                    </span>
                                </div>

                                {/* Details Section */}
                                <div className="p-5 flex-1 flex flex-col justify-between">
                                    <div>
                                        <div className="flex items-start justify-between gap-2 mb-2">
                                            <h3 className="text-lg font-bold text-slate-900 leading-tight group-hover:text-primary-text transition-colors">
                                                {act.title}
                                            </h3>
                                            <button
                                                onClick={() => handleEdit(act)}
                                                className="text-slate-400 hover:text-primary-text transition-colors p-1 rounded-lg hover:bg-primary/5 shrink-0"
                                                title="Edit Activity"
                                                aria-label={`Edit ${act.title}`}
                                            >
                                                <Pencil className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(act.id, act.title)}
                                                className="text-slate-400 hover:text-red-600 transition-colors p-1 rounded-lg hover:bg-red-50 shrink-0"
                                                title="Delete Activity"
                                                aria-label={`Delete ${act.title}`}
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                        <p className="text-sm text-slate-600 line-clamp-2 leading-relaxed mb-4">
                                            {act.description}
                                        </p>
                                    </div>
                                    
                                    <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-slate-500">
                                        <div className="flex items-center gap-1.5">
                                            <Clock className="w-3.5 h-3.5 text-slate-400" />
                                            {eventDateObj.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            <MapPin className="w-3.5 h-3.5 text-slate-400" />
                                            {act.location}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>

            {/* Modern Create Modal */}
            {isModalOpen && (
                <ScheduleActivityModal
                    mode={editingActivity ? 'edit' : 'create'}
                    onClose={closeModal}
                    onSubmit={handleSave}
                    title={title}
                    setTitle={setTitle}
                    location={location}
                    setLocation={setLocation}
                    eventDate={eventDate}
                    setEventDate={setEventDate}
                    description={description}
                    setDescription={setDescription}
                    isSubmitting={isSubmitting}
                />
            )}
        </div>
    );
};
