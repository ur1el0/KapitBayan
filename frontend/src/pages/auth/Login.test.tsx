import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { axiosPublic } from '../../api/axios';
import { useAuth } from '../../context/auth-context';
import { Login } from './Login';

function CurrentPath() {
    return <output data-testid="current-path">{useLocation().pathname}</output>;
}

vi.mock('../../api/axios', () => ({
    axiosPublic: { post: vi.fn() },
}));

vi.mock('../../context/auth-context', () => ({
    useAuth: vi.fn(),
}));

describe('web login role boundaries', () => {
    const login = vi.fn();
    const logout = vi.fn(async () => {});

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useAuth).mockReturnValue({
            user: null,
            login,
            logout,
            isAuthenticated: false,
        } as never);
    });

    it('provides an explicit barangay staff sign-in path without a hidden role switch', () => {
        render(
            <MemoryRouter initialEntries={['/login']}>
                <Login />
            </MemoryRouter>,
        );

        expect(screen.getByRole('link', { name: 'Barangay staff sign in' }))
            .toHaveAttribute('href', '/official-login');
    });

    it('rejects Field Official web login and clears the refresh session cookie', async () => {
        vi.mocked(axiosPublic.post)
            .mockResolvedValueOnce({
                data: {
                    access: 'field-access-token',
                    user: { role: 'FIELD_OFFICIAL' },
                },
            } as never);

        render(
            <MemoryRouter initialEntries={['/official-login']}>
                <Login />
            </MemoryRouter>,
        );

        fireEvent.change(screen.getByPlaceholderText('Enter your official email'), {
            target: { value: 'field.staff@example.gov.ph' },
        });
        fireEvent.change(screen.getByPlaceholderText('........'), {
            target: { value: 'not-a-web-password' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Sign in to Official Portal' }));

        expect(await screen.findByText(/must use the KapitBayan mobile app/i)).toBeInTheDocument();
        expect(axiosPublic.post).toHaveBeenNthCalledWith(1, '/auth/login/', {
            username: 'field.staff@example.gov.ph',
            password: 'not-a-web-password',
        });
        expect(logout).toHaveBeenCalledOnce();
        expect(login).not.toHaveBeenCalled();
    });

    it('allows a Django superuser to use the isolated platform recovery sign-in', async () => {
        vi.mocked(axiosPublic.post).mockResolvedValueOnce({
            data: {
                access: 'platform-access-token',
                user: { role: 'RESIDENT', is_superuser: true },
            },
        } as never);

        render(
            <MemoryRouter initialEntries={['/official-login']}>
                <>
                    <Login />
                    <CurrentPath />
                </>
            </MemoryRouter>,
        );

        fireEvent.change(screen.getByPlaceholderText('Enter your official email'), {
            target: { value: 'platform.operator@example.test' },
        });
        fireEvent.change(screen.getByPlaceholderText('........'), {
            target: { value: 'operator-password' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Sign in to Official Portal' }));

        await waitFor(() => {
            expect(screen.getByTestId('current-path')).toHaveTextContent('/platform/accounts');
        });
        expect(login).toHaveBeenCalledWith('platform-access-token', {
            role: 'RESIDENT',
            is_superuser: true,
        });
        expect(logout).not.toHaveBeenCalled();
    });
});
