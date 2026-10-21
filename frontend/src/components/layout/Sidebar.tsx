import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/auth-context';
import { useLanguage } from '../../context/language-context';
import { LanguageSwitcher } from '../language/LanguageSwitcher';

import { 
    Settings, 
    LogOut, 
    LayoutDashboard, 
    ListOrdered, 
    FileText, 
    Radio, 
    Users, 
    Building,
    HandHeart,
} from 'lucide-react';
import kapitBayanSymbol from '../../assets/kapitbayan/symbol.png';

interface NavItem {
    name: string;
    path: string;
    icon: React.ElementType;
}

const navItems: NavItem[] = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Queue', path: '/queue', icon: ListOrdered },
    { name: 'Documents', path: '/documents', icon: FileText },
    { name: 'Aid Requests', path: '/aid-requests', icon: HandHeart },
    { name: 'Communications', path: '/communications', icon: Radio },
    { name: 'Residents', path: '/residents', icon: Users },
    { name: 'Barangay Profile', path: '/barangay-settings', icon: Building},
];

interface SidebarProps {
    compact?: boolean;
    onNavigate?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ compact = false, onNavigate }) => {
    const { logout } = useAuth();
    const location = useLocation();
    const { t } = useLanguage();

    return (
        <aside
            aria-label={compact ? t('Mobile administration menu') : t('Administration sidebar')}
            className={`${compact ? 'w-full' : 'hidden h-screen w-64 shrink-0 border-r md:flex'} bg-[#F8FAFD] border-[#E2E8F0] flex flex-col justify-between select-none`}
        >
            <div>
                <div className={`${compact ? 'h-14 px-4' : 'h-20 px-6'} flex items-center gap-3`}>
                    <div className="w-9 h-9 overflow-hidden rounded-xl bg-[#092B66] flex items-center justify-center shadow-sm shrink-0">
                        <img src={kapitBayanSymbol} alt="KapitBayan" className="h-full w-full scale-[1.65] object-contain" />
                    </div>
                    <div className="flex flex-col justify-center">
                        <span className="text-[9px] font-bold tracking-[0.14em] text-[#64748b] uppercase leading-tight mt-0.5">
                            {t('BARANGAY AUTHORITY')}
                        </span>
                    </div>
                </div>

                {/* Navigation Items */}
                <nav aria-label={compact ? 'Mobile administration' : 'Admin navigation'} className="px-3.5 py-2">
                    <ul className="space-y-1">
                        {navItems.map((item) => {
                            const isActive =
                                location.pathname === item.path ||
                                (item.path !== '/' && location.pathname.startsWith(item.path));
                            const Icon = item.icon;

                            return (
                                <li key={item.name}>
                                    <NavLink
                                        to={item.path}
                                        onClick={onNavigate}
                                        className={`flex min-h-[44px] items-center gap-3.5 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150 group ${
                                            isActive
                                                ? 'bg-primary/10 text-primary-text font-bold shadow-xs'
                                                : 'text-[#475569] font-medium hover:bg-[#EEF3FA] hover:text-[#0f172a]'
                                        } focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40`}
                                        aria-current={isActive ? 'page' : undefined}
                                    >
                                        <div className="w-5 h-5 flex items-center justify-center shrink-0">
                                            <Icon className={`w-5 h-5 transition-colors duration-150 ${
                                                isActive
                                                    ? 'text-primary-text'
                                                    : 'text-[#64748b] group-hover:text-[#0f172a]'
                                            }`} />
                                        </div>
                                        <span>{t(item.name)}</span>
                                    </NavLink>
                                </li>
                            );
                        })}
                    </ul>
                </nav>
            </div>

            <div className="px-3.5 pb-6 space-y-1">
                {compact && (
                    <div className="px-4 py-3">
                        <LanguageSwitcher />
                    </div>
                )}
                <NavLink
                    to="/settings"
                    onClick={onNavigate}
                    aria-current={location.pathname === '/settings' ? 'page' : undefined}
                    className={({ isActive }) =>
                        `flex min-h-[44px] items-center gap-3.5 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group ${
                            isActive
                                ? 'bg-primary/10 text-primary-text font-bold shadow-xs'
                                : 'text-[#475569] hover:bg-[#EEF3FA] hover:text-[#0f172a]'
                        } focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40`
                    }
                >
                    <div className="w-5 h-5 flex items-center justify-center shrink-0">
                        <Settings className="w-[19px] h-[19px] text-[#475569] group-hover:text-[#0f172a] transition-colors" />
                    </div>
                    <span>{t('Settings')}</span>
                </NavLink>

                <button
                    onClick={async () => {
                        onNavigate?.();
                        await logout();
                    }}
                    type="button"
                    aria-label={t('Logout')}
                    className="w-full flex min-h-[44px] items-center gap-3.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-[#DC2626] hover:bg-red-50 hover:text-red-700 transition-all duration-150 text-left cursor-pointer group"
                >
                    <div className="w-5 h-5 flex items-center justify-center shrink-0">
                        <LogOut className="w-[19px] h-[19px] text-[#DC2626] group-hover:text-red-700 transition-colors" />
                    </div>
                    <span>{t('Logout')}</span>
                </button>
            </div>
        </aside>
    );
};
