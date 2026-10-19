import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/auth-context';
import { RouteLoadingFallback } from './RouteLoadingFallback';

interface ProtectedRouteProps {
    allowedRoles?: string[];
    requireSuperuser?: boolean;
}

export const ProtectedRoute = ({ allowedRoles, requireSuperuser = false }: ProtectedRouteProps) => {
    const { isAuthenticated, isAuthReady, user } = useAuth();
    const location = useLocation();

    if (isAuthReady === false) {
        return <RouteLoadingFallback />;
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (!requireSuperuser && user?.is_superuser) {
        return <Navigate to="/platform/accounts" replace />;
    }

    if (requireSuperuser && !user?.is_superuser) {
        return <Navigate to="/" replace />;
    }

    // If specific roles are required, verify user's role
    if (allowedRoles && (!user?.role || !allowedRoles.includes(user.role))) {
        if (user?.role === 'DILG_ADMIN') {
            return <Navigate to="/dilg/barangay-applications" replace />;
        }
        if (user?.role === 'FIELD_OFFICIAL') {
            return <Navigate to="/field-official-mobile" replace />;
        }
        // Redirect residents away from admin routes to resident portal
        if (user?.role === 'RESIDENT') {
            return <Navigate to="/portal" replace />;
        }
        // Redirect officials away from resident routes to admin dashboard
        return <Navigate to="/dashboard" replace />;
    }

    return <Outlet />;
};
