import React, { useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/auth-context';
import { 
    Bell, 
    HelpCircle,
    Menu,
    X,
} from 'lucide-react';
import { Sidebar } from './Sidebar';

export const AdminLayout: React.FC = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [isMobileNavigationOpen, setIsMobileNavigationOpen] = useState(false);

    const userInitial = user?.full_name 
        ? user.full_name.charAt(0).toUpperCase() 
        : (user?.username?.charAt(0).toUpperCase() || 'J');
        
    const userName = user?.full_name || user?.username || 'Admin Juan';

    return (
        <div className="min-h-screen min-h-[100dvh] flex flex-col md:h-screen md:flex-row bg-[#F0F4FA] text-slate-900 font-sans antialiased md:overflow-hidden">
            {/* Sidebar Navigation */}
            <Sidebar />

            {/* Main Right Content Section */}
            <div className="flex min-h-screen min-h-[100dvh] min-w-0 flex-1 flex-col md:min-h-0 md:overflow-hidden">
                {/* Top Navigation Bar */}
                <header className="h-16 sm:h-20 bg-transparent flex items-center justify-between gap-3 px-4 sm:px-6 lg:px-8 shrink-0">
                    <div className="flex min-w-0 items-center gap-3">
                        <button
                            type="button"
                            onClick={() => setIsMobileNavigationOpen((open) => !open)}
                            aria-label={isMobileNavigationOpen ? 'Close navigation menu' : 'Open navigation menu'}
                            aria-expanded={isMobileNavigationOpen}
                            aria-controls="admin-mobile-navigation"
                            className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-xs transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-admin/40"
                        >
                            {isMobileNavigationOpen ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
                        </button>
                        <span className="truncate text-sm font-semibold text-slate-700 sm:text-base">
                            KapitBayan administration
                        </span>
                    </div>

                    {/* Right Header Controls */}
                    <div className="flex shrink-0 items-center gap-2 sm:gap-4">
                        <button type="button" onClick={() => navigate('/notifications')} className="rounded-full p-2 text-primary-text transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-admin/40" aria-label="Notifications">
                            <Bell className="w-5 h-5" aria-hidden="true" />
                        </button>
                        
                        <button type="button" onClick={() => navigate('/faqs')} className="rounded-full p-2 text-primary-text transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-admin/40" aria-label="Help and information">
                            <HelpCircle className="w-5 h-5" aria-hidden="true" />
                        </button>

                        <button type="button" onClick={() => navigate('/profile')} aria-label={`Open profile for ${userName}`} className="flex items-center gap-2 rounded-xl pl-1 sm:gap-3 sm:pl-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-admin/40">
                            <span className="hidden max-w-40 truncate text-sm font-bold text-slate-800 sm:block">{userName}</span>
                            <div className="w-9 h-9 rounded-xl bg-slate-300 text-slate-700 font-bold flex items-center justify-center text-sm shadow-xs border border-slate-200">
                                {userInitial}
                            </div>
                        </button>
                    </div>
                </header>

                <div
                    id="admin-mobile-navigation"
                    hidden={!isMobileNavigationOpen}
                    className="border-y border-slate-200 bg-white shadow-sm md:hidden"
                >
                    <Sidebar compact onNavigate={() => setIsMobileNavigationOpen(false)} />
                </div>

                {/* Page Content View */}
                <main className="flex flex-1 flex-col justify-between overflow-y-auto px-4 pb-8 sm:px-6 lg:px-8">
                    <div>
                        <Outlet />
                    </div>

                    {/* Footer */}
                    <footer className="pt-8 text-xs text-slate-600 font-medium">
                        © 2026 KapitBayan Admin
                    </footer>
                </main>
            </div>
        </div>
    );
};
