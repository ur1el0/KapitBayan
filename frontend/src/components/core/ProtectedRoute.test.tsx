import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { useAuth } from '../../context/auth-context';
import { ProtectedRoute } from './ProtectedRoute';

vi.mock('../../context/auth-context', () => ({ useAuth: vi.fn() }));

describe('ProtectedRoute', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useAuth).mockReturnValue({
            user: null,
            isAuthenticated: false,
            isAuthReady: false,
            login: vi.fn(),
            logout: vi.fn(),
            updateBarangayPrimaryColor: vi.fn(),
        });
    });

    it('waits for the refresh-cookie session check before redirecting to login', () => {
        render(
            <MemoryRouter initialEntries={['/protected']}>
                <Routes>
                    <Route element={<ProtectedRoute />}>
                        <Route path="/protected" element={<div>Private content</div>} />
                    </Route>
                    <Route path="/login" element={<div>Login form</div>} />
                </Routes>
            </MemoryRouter>,
        );

        expect(screen.getByRole('status')).toHaveTextContent('Loading page');
        expect(screen.queryByText('Login form')).not.toBeInTheDocument();
        expect(screen.queryByText('Private content')).not.toBeInTheDocument();
    });

    it('sends a Field Official who opens an admin URL to mobile-app guidance', async () => {
        vi.mocked(useAuth).mockReturnValue({
            user: { role: 'FIELD_OFFICIAL' },
            isAuthenticated: true,
            isAuthReady: true,
            login: vi.fn(),
            logout: vi.fn(),
            updateBarangayPrimaryColor: vi.fn(),
        } as never);

        render(
            <MemoryRouter initialEntries={['/dashboard']}>
                <Routes>
                    <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
                        <Route path="/dashboard" element={<p>Admin dashboard</p>} />
                    </Route>
                    <Route path="/field-official-mobile" element={<p>Open KapitBayan on mobile</p>} />
                </Routes>
            </MemoryRouter>,
        );

        expect(await screen.findByText('Open KapitBayan on mobile')).toBeInTheDocument();
        expect(screen.queryByText('Admin dashboard')).not.toBeInTheDocument();
    });

    it('keeps platform superusers out of resident and barangay workspaces', async () => {
        vi.mocked(useAuth).mockReturnValue({
            user: { role: 'RESIDENT', is_superuser: true },
            isAuthenticated: true,
            isAuthReady: true,
            login: vi.fn(),
            logout: vi.fn(),
            updateBarangayPrimaryColor: vi.fn(),
        } as never);

        render(
            <MemoryRouter initialEntries={['/portal']}>
                <Routes>
                    <Route path="/" element={<p>Home</p>} />
                    <Route element={<ProtectedRoute allowedRoles={['RESIDENT']} />}>
                        <Route path="/portal" element={<p>Resident portal</p>} />
                    </Route>
                    <Route element={<ProtectedRoute requireSuperuser />}>
                        <Route path="/platform/accounts" element={<p>Platform account support</p>} />
                    </Route>
                </Routes>
            </MemoryRouter>,
        );

        expect(await screen.findByText('Platform account support')).toBeInTheDocument();
        expect(screen.queryByText('Resident portal')).not.toBeInTheDocument();
    });
});
