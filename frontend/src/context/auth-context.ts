import { createContext, useContext } from "react";

export interface ResidentProfile {
    id?: number | string
    full_name?: string
    birth_date?: string | null
    voter_status?: boolean | null
    contact_number?: string | null
    purok?: string | null
    is_verified?: boolean
}

export interface User {
    id?: number | string
    email?: string
    username?: string
    full_name?: string
    profile_picture?: string | null
    role?: string
    is_superuser?: boolean
    email_alerts?: boolean
    push_alerts?: boolean
    profile?: ResidentProfile
    barangay_id?: number | string | null
    barangay?: {
        id?: number | string
        name?: string
        primary_color?: string
    } | null
}

export interface AuthContextType {
    user: User | null
    login: (token: string, userData?: User) => void
    logout: () => Promise<void>
    isAuthenticated: boolean
    isAuthReady?: boolean
    updateBarangayPrimaryColor: (primaryColor: string) => void
    updateUser?: (updates: Partial<User>) => void
}

export const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
