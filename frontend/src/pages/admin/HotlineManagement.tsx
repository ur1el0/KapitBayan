import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { axiosPrivate } from '../../api/axios'
import { Phone, Plus, Trash2, Pencil } from 'lucide-react'
import { AddHotlineModal } from '../../components/hotlines/AddHotlineModal'
import { InlineErrorState } from '../../components/ui/InlineErrorState'

interface Hotline {
    id: number
    name: string
    number: string
    category: string
    category_display: string
    is_active: boolean
}

const CATEGORIES = ['POLICE', 'FIRE', 'MEDICAL', 'BARANGAY', 'OTHER']
const EMPTY_FORM = { name: '', number: '', category: 'OTHER', is_active: true }

const getCategoryBadge = (category: string) => {
    switch (category) {
        case 'POLICE': return 'bg-blue-100 text-blue-800 border-blue-200'
        case 'FIRE': return 'bg-orange-100 text-orange-800 border-orange-200'
        case 'MEDICAL': return 'bg-emerald-100 text-emerald-800 border-emerald-200'
        case 'BARANGAY': return 'bg-indigo-100 text-indigo-800 border-indigo-200'
        default: return 'bg-slate-100 text-slate-700 border-slate-200'
    }
}

export const HotlineManagement: React.FC = () => {
    const [hotlines, setHotlines] = useState<Hotline[]>([])
    const [loading, setLoading] = useState(true)
    const [loadError, setLoadError] = useState(false)
    const [retrying, setRetrying] = useState(false)
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [editingHotline, setEditingHotline] = useState<Hotline | null>(null)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [form, setForm] = useState(EMPTY_FORM)

    const closeModal = () => {
        setIsModalOpen(false)
        setEditingHotline(null)
        setForm(EMPTY_FORM)
    }

    const openCreateModal = () => {
        setEditingHotline(null)
        setForm(EMPTY_FORM)
        setIsModalOpen(true)
    }

    const handleEdit = (hotline: Hotline) => {
        setEditingHotline(hotline)
        setForm({
            name: hotline.name,
            number: hotline.number,
            category: hotline.category,
            is_active: hotline.is_active,
        })
        setIsModalOpen(true)
    }

    const fetchHotlines = async (isRetry = false) => {
        if (isRetry) setRetrying(true)
        try {
            const res = await axiosPrivate.get('/hotlines/')
            setHotlines(res.data.results || res.data)
            setLoadError(false)
        } catch {
            setLoadError(true)
        } finally {
            setLoading(false)
            setRetrying(false)
        }
    }

    useEffect(() => { fetchHotlines() }, [])

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsSubmitting(true)
        try {
            if (editingHotline) {
                const res = await axiosPrivate.patch(`/hotlines/${editingHotline.id}/`, form)
                setHotlines(prev => prev.map(hotline => hotline.id === editingHotline.id ? res.data : hotline))
                toast.success('Hotline updated successfully.')
            } else {
                const res = await axiosPrivate.post('/hotlines/', form)
                setHotlines(prev => [...prev, res.data])
                toast.success('Hotline added successfully.')
            }
            closeModal()
        } catch {
            toast.error(editingHotline ? 'Failed to update hotline.' : 'Failed to add hotline.')
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleDelete = async (id: number) => {
        if (!window.confirm('Delete this hotline?')) return
        try {
            await axiosPrivate.delete(`/hotlines/${id}/`)
            setHotlines(prev => prev.filter(h => h.id !== id))
            toast.success('Hotline removed.')
        } catch {
            toast.error('Failed to delete hotline.')
        }
    }

    if (loading) return <div className="p-8 text-slate-500">Loading hotlines...</div>

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Emergency Hotlines</h1>
                    <p className="text-slate-500 mt-1">Manage emergency contacts visible to residents.</p>
                </div>
                <button
                    onClick={openCreateModal}
                    className="flex items-center gap-2 bg-primary hover:bg-primary-hover text-primary-foreground px-4 py-2 rounded-md text-sm font-medium transition-colors"
                >
                    <Plus size={16} /> Add Hotline
                </button>
            </div>

            {/* Table */}
            <div className="bg-white shadow-sm border border-slate-200 rounded-lg overflow-hidden">
                {loadError ? (
                    <InlineErrorState
                        message="We couldn't load emergency hotlines."
                        onRetry={() => { void fetchHotlines(true) }}
                        retrying={retrying}
                    />
                ) : (
                <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Name</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Number</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Category</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-slate-200">
                        {hotlines.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-8 text-center text-sm text-slate-500">No hotlines added yet.</td>
                            </tr>
                        ) : (
                            hotlines.map(h => (
                                <tr key={h.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <Phone size={16} className="text-slate-400" />
                                            <span className="text-sm font-semibold text-slate-900">{h.name}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-700 font-mono">{h.number}</td>
                                    <td className="px-6 py-4">
                                        <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${getCategoryBadge(h.category)}`}>
                                            {h.category_display}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`text-xs font-semibold ${h.is_active ? 'text-emerald-700' : 'text-slate-500'}`}>
                                            {h.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <button
                                                onClick={() => handleEdit(h)}
                                                className="text-slate-500 hover:text-primary-text transition-colors"
                                                aria-label={`Edit ${h.name}`}
                                                title="Edit hotline"
                                            >
                                                <Pencil size={16} />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(h.id)}
                                                className="text-rose-500 hover:text-rose-700 transition-colors"
                                                aria-label={`Delete ${h.name}`}
                                                title="Delete hotline"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
                )}
            </div>

            {/* Add Hotline Modal */}
            {isModalOpen && (
                <AddHotlineModal
                    mode={editingHotline ? 'edit' : 'create'}
                    onClose={closeModal}
                    onSubmit={handleSave}
                    form={form}
                    setForm={setForm}
                    categories={CATEGORIES}
                    isSubmitting={isSubmitting}
                />
            )}
        </div>
    )
}
