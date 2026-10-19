import React from 'react';
import { useAuth } from '../../context/auth-context';
import { User, Mail, Shield, Calendar, Phone } from 'lucide-react';

export const AdminProfile: React.FC = () => {
    const { user } = useAuth();

    if (!user) return null;

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <h1 className="text-2xl font-extrabold text-[#0f172a] tracking-tight">Admin Profile</h1>
            
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                {/* Banner */}
                <div className="h-32 bg-gradient-to-r from-primary to-primary-hover"></div>
                
                <div className="px-8 pb-8 relative">
                    {/* Avatar Profile Picture */}
                    <div className="absolute -top-12 left-8 w-24 h-24 bg-white rounded-full p-1 shadow-md">
                        <div className="w-full h-full rounded-full bg-primary/10 flex items-center justify-center text-primary-text text-4xl font-black">
                            {(user.username ?? '').charAt(0).toUpperCase()}
                        </div>
                    </div>
                    
                    <div className="pt-16 flex flex-col sm:flex-row justify-between items-start gap-4">
                        <div>
                            <h2 className="text-2xl font-bold text-slate-900">{user.email || user.username}</h2>
                            <p className="text-sm text-slate-500">Sign-in identity</p>
                            <p className="text-slate-500 font-medium">Barangay Official</p>
                        </div>
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-primary/10 text-primary-text border border-primary/20">
                            <Shield className="w-3.5 h-3.5" /> Administrator Access
                        </span>
                    </div>

                    <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-4">
                            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">Contact Information</h3>
                            <div className="space-y-3">
                                <div className="flex items-center gap-3 text-sm text-slate-700">
                                    <Mail className="w-4 h-4 text-slate-400" />
                                    {user.email || 'No email provided'}
                                </div>
                                <div className="flex items-center gap-3 text-sm text-slate-700">
                                    <Phone className="w-4 h-4 text-slate-400" />
                                    +63 (Barangay Office Line)
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">Account Details</h3>
                            <div className="space-y-3">
                                <div className="flex items-center gap-3 text-sm text-slate-700">
                                    <User className="w-4 h-4 text-slate-400" />
                                    Role ID: {user.id}
                                </div>
                                <div className="flex items-center gap-3 text-sm text-slate-700">
                                    <Calendar className="w-4 h-4 text-slate-400" />
                                    Account Active
                                </div>
                            </div>
                        </div>
                    </div>
                    
                </div>
            </div>
        </div>
    );
};
