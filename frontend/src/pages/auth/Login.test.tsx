import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { axiosPublic } from '../../api/axios';
import { useAuth } from '../../context/auth-context';
import { Login } from './Login';

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

        fireEvent.change(screen.getByPlaceholderText('Enter your username or email'), {
            target: { value: 'field.staff@example.gov.ph' },
        });
        fireEvent.change(screen.getByPlaceholderText('........'), {
            target: { value: 'not-a-web-password' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Login as Barangay Official' }));

        expect(await screen.findByText(/must use the KapitBayan mobile app/i)).toBeInTheDocument();
        expect(axiosPublic.post).toHaveBeenNthCalledWith(1, '/auth/login/', {
            username: 'field.staff@example.gov.ph',
            password: 'not-a-web-password',
        });
        expect(logout).toHaveBeenCalledOnce();
        expect(login).not.toHaveBeenCalled();
    });
});
