import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/auth-context';
import { 
    FileText, 
    ListOrdered, 
    Radio, 
    LogOut, 
    Building2,
    HandHeart,
    CircleHelp,
    Settings,
} from 'lucide-react';
import kapitBayanSymbol from '../../assets/kapitbayan/symbol.png';

export const CitizenLayout: React.FC = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const displayName = user?.full_name || user?.username || 'Resident';
    const barangayName = user?.barangay?.name || 'Barangay Ibabang Dupay';

    const navLinkClass = ({ isActive }: { isActive: boolean }) =>
        `flex min-h-[44px] shrink-0 items-center gap-2 whitespace-nowrap rounded-xl px-2 py-2 text-sm font-semibold transition-all touch-manipulation ${
            isActive
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-primary-foreground opacity-75 hover:opacity-100 hover:bg-white/10'
        }`;

    return (
        <div className="min-h-screen min-h-[100dvh] flex flex-col bg-[#F8FAFD] text-slate-900 font-sans antialiased">
            {/* Top Citizen Navigation Bar */}
            <header className="bg-primary text-primary-foreground sticky top-0 z-50 shadow-md">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-20">
                        {/* Left: Brand & Barangay Badge */}
                        <div className="flex items-center gap-4 min-w-0">
                            <div className="w-10 h-10 overflow-hidden rounded-xl bg-[#092B66] border border-white/15 flex items-center justify-center shadow-inner shrink-0">
                                <img src={kapitBayanSymbol} alt="" className="h-full w-full scale-[1.65] object-contain" />
                            </div>
                            <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                    <span className="text-xl font-bold tracking-tight text-primary-foreground leading-none">
                                        KapitBayan
                                    </span>
                                    <span className="hidden sm:inline-flex px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-primary-foreground text-primary shrink-0">
                                        Resident Portal
                                    </span>
                                </div>
                                <div className="flex items-center gap-1.5 text-xs text-primary-foreground opacity-80 font-medium mt-1">
                                    <Building2 className="w-3.5 h-3.5 text-primary-foreground shrink-0" />
                                    <span className="truncate max-w-[160px] sm:max-w-xs" title={barangayName}>{barangayName}</span>
                                </div>
                            </div>
                        </div>

                        {/* Center: Main Navigation Tabs */}
                        <nav aria-label="Resident navigation" className="hidden xl:flex shrink-0 items-center gap-1 rounded-2xl border border-white/10 bg-white/5 p-1">
                            <NavLink to="/portal/documents" aria-label="Documents & Clearances" className={navLinkClass}>
                                <FileText className="w-4 h-4" />
                                <span aria-hidden="true">Documents</span>
                                <span className="sr-only">Documents &amp; Clearances</span>
                            </NavLink>

                            <NavLink to="/portal/queue" aria-label="Live Queue Ticker" className={navLinkClass}>
                                <ListOrdered className="w-4 h-4" />
                                <span aria-hidden="true">Queue</span>
                                <span className="sr-only">Live Queue Ticker</span>
                            </NavLink>

                            <NavLink to="/portal/bulletin" aria-label="Community Bulletin" className={navLinkClass}>
                                <Radio className="w-4 h-4" />
                                <span aria-hidden="true">Bulletin</span>
                                <span className="sr-only">Community Bulletin</span>
                            </NavLink>
                            <NavLink to="/portal/aid" aria-label="Assistance" className={navLinkClass}>
                                <HandHeart className="w-4 h-4" />
                                <span>Assistance</span>
                            </NavLink>
                            <NavLink to="/portal/help" aria-label="FAQs" className={navLinkClass}>
                                <CircleHelp className="w-4 h-4" aria-hidden="true" />
                                <span>FAQs</span>
                            </NavLink>
                        </nav>

                        {/* Right: Resident Profile Pill & Logout */}
                        <div className="flex items-center gap-3 shrink-0">
                            <NavLink
                                to="/portal/profile"
                                aria-label={`Profile and settings for ${displayName}`}
                                title="Profile and settings"
                                className={({ isActive }) => `flex min-h-[44px] items-center gap-2 rounded-full border px-2 sm:px-3.5 py-1.5 max-w-[190px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary ${isActive ? 'border-white/40 bg-white/20' : 'border-white/10 bg-white/5 hover:bg-white/10'}`}
                            >
                                <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0">
                                    {displayName.charAt(0).toUpperCase()}
                                </div>
                                <div className="hidden sm:flex flex-col text-left min-w-0">
                                    <span className="text-xs font-bold text-primary-foreground leading-tight truncate">
                                        {displayName}
                                    </span>
                                    <span className="flex items-center gap-1 text-[10px] text-primary-foreground/75 font-semibold shrink-0">
                                        <Settings className="w-3 h-3" aria-hidden="true" />
                                        Profile &amp; Settings
                                    </span>
                                </div>
                            </NavLink>

                            <button
                                type="button"
                                onClick={handleLogout}
                                title="Log Out"
                                aria-label="Log out"
                                className="flex min-h-[44px] items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-primary-foreground hover:bg-rose-500/20 border border-rose-500/30 transition-all cursor-pointer touch-manipulation"
                            >
                                <LogOut className="w-4 h-4" />
                                <span className="hidden sm:inline">Log Out</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Mobile Navigation Row (for smaller screens & kiosks) */}
                <nav aria-label="Resident navigation" className="xl:hidden flex gap-1 overflow-x-auto border-t border-white/10 px-2 py-1.5">
                    <NavLink to="/portal/documents" className={navLinkClass}>
                        <FileText className="w-4 h-4" />
                        <span className="text-xs">Documents</span>
                    </NavLink>
                    <NavLink to="/portal/queue" className={navLinkClass}>
                        <ListOrdered className="w-4 h-4" />
                        <span className="text-xs">Queue</span>
                    </NavLink>
                    <NavLink to="/portal/bulletin" className={navLinkClass}>
                        <Radio className="w-4 h-4" />
                        <span className="text-xs">Bulletin</span>
                    </NavLink>
                    <NavLink to="/portal/aid" className={navLinkClass}>
                        <HandHeart className="w-4 h-4" />
                        <span className="text-xs">Aid</span>
                    </NavLink>
                    <NavLink to="/portal/help" className={`${navLinkClass} whitespace-nowrap`}>
                        <CircleHelp className="w-4 h-4" aria-hidden="true" />
                        <span className="text-xs">FAQs</span>
                    </NavLink>
                    <NavLink to="/portal/profile" className={`${navLinkClass} whitespace-nowrap`}>
                        <Settings className="w-4 h-4" aria-hidden="true" />
                        <span className="text-xs">Profile &amp; Settings</span>
                    </NavLink>
                </nav>
            </header>

            {/* Main Content Viewport */}
            <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Outlet />
            </main>

            {/* Footer */}
            <footer className="border-t border-slate-200 bg-white/60 py-4 text-center text-xs text-slate-500">
                Republic of the Philippines • Barangay Information and Service Management System • KapitBayan
            </footer>
        </div>
    );
};
