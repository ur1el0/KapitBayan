import React, { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { AuthContext, type User } from "./auth-context";
import { axiosPrivate } from "../api/axios";
import {
    clearAccessToken,
    clearExplicitLogout,
    EXPLICIT_LOGOUT_KEY,
    hasExplicitLogout,
    markExplicitLogout,
    setAccessToken,
} from "../api/accessToken";

const DEFAULT_PRIMARY_COLOR = '#082B66';
const AUTHENTICATED_ROLES = new Set([
    'ADMIN',
    'RESIDENT',
    'FIELD_OFFICIAL',
]);

function isUserProfile(value: unknown): value is User {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        return false;
    }

    const profile = value as Record<string, unknown>;
    const hasValidId =
        (typeof profile.id === 'number' && Number.isSafeInteger(profile.id) && profile.id > 0) ||
        (typeof profile.id === 'string' && profile.id.trim().length > 0);

    return (
        hasValidId &&
        typeof profile.username === 'string' &&
        profile.username.trim().length > 0 &&
        typeof profile.role === 'string' &&
        AUTHENTICATED_ROLES.has(profile.role)
    );
}

function hasLogoutConfirmation(value: unknown): boolean {
    return (
        typeof value === 'object' &&
        value !== null &&
        !Array.isArray(value) &&
        (value as Record<string, unknown>).detail === 'Successfully logged out.'
    );
}

const applyBarangayTheme = (primaryColor?: string) => {
    const color =
        primaryColor && /^#[0-9a-fA-F]{6}$/.test(primaryColor)
            ? primaryColor.toUpperCase()
            : DEFAULT_PRIMARY_COLOR;

    const red = Number.parseInt(color.slice(1, 3), 16);
    const green = Number.parseInt(color.slice(3, 5), 16);
    const blue = Number.parseInt(color.slice(5, 7), 16);

    const linearize = (channel: number) => {
        const value = channel / 255;
        return value <= 0.04045
            ? value / 12.92
            : ((value + 0.055) / 1.055) ** 2.4;
    };

    const luminance =
        0.2126 * linearize(red) +
        0.7152 * linearize(green) +
        0.0722 * linearize(blue);

    const whiteContrast = 1.05 / (luminance + 0.05);
    const darkContrast = (luminance + 0.05) / (linearize(15) + 0.05);
    const foreground = darkContrast >= whiteContrast ? '#0F172A' : '#FFFFFF';

    let primaryTextColor = color;
    if (whiteContrast < 4.5) {
        let lowerScale = 0;
        let upperScale = 1;
        for (let index = 0; index < 24; index += 1) {
            const scale = (lowerScale + upperScale) / 2;
            const scaledLuminance =
                0.2126 * linearize(red * scale) +
                0.7152 * linearize(green * scale) +
                0.0722 * linearize(blue * scale);
            if (1.05 / (scaledLuminance + 0.05) >= 4.5) {
                lowerScale = scale;
            } else {
                upperScale = scale;
            }
        }
        primaryTextColor =
            '#' +
            [red, green, blue]
                .map((channel) =>
                    Math.round(channel * lowerScale)
                        .toString(16)
                        .padStart(2, '0'),
                )
                .join('')
                .toUpperCase();
    }

    const hoverChannels = [red, green, blue].map((channel) =>
        foreground === '#FFFFFF'
            ? Math.round(channel * 0.85)
            : Math.round(channel + (255 - channel) * 0.15),
    );

    const rootStyle = document.documentElement.style;
    rootStyle.setProperty('--brand-primary', color);
    rootStyle.setProperty('--brand-primary-rgb', red + ' ' + green + ' ' + blue);
    rootStyle.setProperty(
        '--brand-primary-hover',
        'rgb(' + hoverChannels.join(' ') + ')',
    );
    rootStyle.setProperty('--brand-primary-foreground', foreground);
    rootStyle.setProperty('--brand-primary-text', primaryTextColor);
};

interface AuthProviderProps {
    children: ReactNode;
    restoreSession?: boolean;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children, restoreSession = true }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isAuthReady, setIsAuthReady] = useState(!restoreSession);
    const authActionVersion = useRef(0);

    useEffect(() => {
        applyBarangayTheme(user?.barangay?.primary_color);
    }, [user?.barangay?.primary_color]);

    useEffect(() => {
        if (!restoreSession) return;
        if (hasExplicitLogout()) {
            clearAccessToken();
            setUser(null);
            setIsAuthReady(true);
            return;
        }
        let active = true;
        const initialActionVersion = authActionVersion.current;

        const handleSessionExpired = () => {
            authActionVersion.current += 1;
            clearAccessToken();
            setUser(null);
            setIsAuthReady(true);
        };
        const handleCrossTabLogout = (event: StorageEvent) => {
            if (event.key === EXPLICIT_LOGOUT_KEY && event.newValue === 'true') {
                handleSessionExpired();
            }
        };
        window.addEventListener('gridy:session-expired', handleSessionExpired);
        window.addEventListener('storage', handleCrossTabLogout);

        axiosPrivate.get('/auth/me/')
            .then((response) => {
                if (!isUserProfile(response.data)) {
                    throw new Error('Invalid authenticated profile response.');
                }
                if (active && authActionVersion.current === initialActionVersion) {
                    setUser(response.data);
                }
            })
            .catch((error) => {
                if (active && authActionVersion.current === initialActionVersion) {
                    clearAccessToken();
                    setUser(null);
                }
                if (error?.response?.status !== 401) {
                    console.error('Failed to load the authenticated profile');
                }
            })
            .finally(() => {
                if (active && authActionVersion.current === initialActionVersion) {
                    setIsAuthReady(true);
                }
            });

        return () => {
            active = false;
            window.removeEventListener('gridy:session-expired', handleSessionExpired);
            window.removeEventListener('storage', handleCrossTabLogout);
        };
    }, [restoreSession]);

    const login = (token: string, userData?: User) => {
        authActionVersion.current += 1;
        let authenticatedUser: User | null = null;
        if (typeof token === 'string' && token.trim().length > 0 && userData && isUserProfile(userData)) {
            authenticatedUser = userData;
        } else if (typeof token === 'string' && token.trim().length > 0 && !userData) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                const tokenUser: User = {
                    id: payload.user_id,
                    username: payload.username,
                    full_name: payload.full_name,
                    role: payload.role,
                };
                if (isUserProfile(tokenUser)) {
                    authenticatedUser = tokenUser;
                }
            } catch {
                // Treat unparseable token claims as an invalid login response.
            }
        }

        if (!authenticatedUser) {
            clearAccessToken();
            setUser(null);
            setIsAuthReady(true);
            console.error('Login response did not contain a valid authenticated profile.');
            return;
        }

        clearExplicitLogout();
        setAccessToken(token);
        setIsAuthReady(true);
        setUser(authenticatedUser);
    };

    const updateUser = useCallback((updates: Partial<User>) => {
        setUser((currentUser) =>
            currentUser ? { ...currentUser, ...updates } : currentUser,
        );
    }, []);

    const updateBarangayPrimaryColor = (primaryColor: string) => {
        setUser((currentUser) => {
            if (!currentUser) return currentUser;

            return {
                ...currentUser,
                barangay: {
                    ...(currentUser.barangay ?? {}),
                    primary_color: primaryColor,
                },
            };
        });
    };

    const logout = async () => {
        authActionVersion.current += 1;
        markExplicitLogout();
        clearAccessToken();
        setUser(null);
        setIsAuthReady(true);

        try {
            // Tell the backend to blacklist the session and destroy the HttpOnly cookie.
            const response = await axiosPrivate.post('/auth/logout/');
            if (!hasLogoutConfirmation(response.data)) {
                throw new Error('Invalid server logout response.');
            }
        } catch {
            console.error("Server logout failed, but local state will be cleared.");
        }
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                login,
                logout,
                isAuthenticated: !!user,
                isAuthReady,
                updateBarangayPrimaryColor,
                updateUser,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};
