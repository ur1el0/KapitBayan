import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate, axiosPublic } from '../../api/axios';
import { AdminLayout } from '../../components/layout/AdminLayout';
import { LanguageProvider } from '../../context/language-context';
import { Dashboard } from '../admin/Dashboard';
import { Login } from './Login';

vi.mock('../../api/axios', () => ({
    axiosPublic: { post: vi.fn() },
    axiosPrivate: {
        get: vi.fn().mockResolvedValue({ data: { count: 0 } }),
        defaults: { baseURL: 'http://localhost:8000' },
    },
}));

vi.mock('../../context/auth-context', () => ({
    useAuth: () => ({
        user: { role: 'ADMIN', username: 'staff', full_name: 'Barangay Staff' },
        login: vi.fn(),
        logout: vi.fn(),
    }),
}));

describe('official web language flow', () => {
    beforeEach(() => {
        window.localStorage.clear();
        vi.clearAllMocks();
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url === '/admin-notifications/unread_count/') {
                return Promise.resolve({ data: { count: 0 } }) as never;
            }
            if (url === '/dashboard/summary/') {
                return Promise.resolve({
                    data: {
                        total_residents: 1,
                        document_requests: { pending: 0 },
                        issue_reports: {
                            in_progress: 0,
                            scenario_breakdown: {
                                peace_and_order: 0,
                                public_health: 0,
                                infrastructure: 0,
                                environment: 0,
                            },
                        },
                    },
                }) as never;
            }
            return Promise.resolve({ data: { results: [] } }) as never;
        });
        vi.mocked(axiosPublic.post).mockResolvedValue({
            data: { access: 'admin-access-token', user: { role: 'ADMIN' } },
        } as never);
    });

    it('keeps Filipino selected from official sign-in through the admin route', async () => {
        render(
            <LanguageProvider>
                <MemoryRouter initialEntries={['/official-login']}>
                    <Routes>
                        <Route path="/official-login" element={<Login />} />
                        <Route element={<AdminLayout />}>
                            <Route path="/dashboard" element={<Dashboard />} />
                        </Route>
                    </Routes>
                </MemoryRouter>
            </LanguageProvider>,
        );

        fireEvent.click(screen.getByRole('button', { name: 'Filipino (Tagalog)' }));
        expect(screen.getByText('Opisyal na Kawani')).toBeInTheDocument();
        expect(window.localStorage.getItem('gridy-resident-language')).toBe('fil');

        fireEvent.change(screen.getByPlaceholderText('Ilagay ang iyong opisyal na email'), {
            target: { value: 'staff@example.gov.ph' },
        });
        fireEvent.change(screen.getByPlaceholderText('........'), {
            target: { value: 'valid-password' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Mag-login sa Opisyal na Portal' }));

        expect(await screen.findByRole('heading', { name: 'Pangkalahatang-tanaw ng Administrasyon' })).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Pila' })).toBeInTheDocument();
        expect(await screen.findByText('Kabuuang Rehistradong Residente')).toBeInTheDocument();
    });
});
