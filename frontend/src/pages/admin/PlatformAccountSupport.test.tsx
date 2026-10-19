import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { fetchPlatformAccounts } from '../../api/platformAccountSupport';
import { useAuth } from '../../context/auth-context';
import { PlatformAccountSupport } from './PlatformAccountSupport';

vi.mock('../../api/platformAccountSupport', () => ({
    fetchPlatformAccounts: vi.fn(),
    correctPlatformAccountEmail: vi.fn(),
    sendPlatformAccountRecoveryLink: vi.fn(),
    setPlatformAccountActive: vi.fn(),
}));

vi.mock('../../context/auth-context', () => ({ useAuth: vi.fn() }));

describe('Barangay Operator account support', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(fetchPlatformAccounts).mockResolvedValue({
            count: 0,
            next: null,
            previous: null,
            results: [],
        });
        vi.mocked(useAuth).mockReturnValue({
            user: { role: 'BARANGAY_OPERATOR' },
            logout: vi.fn(),
        } as never);
    });

    it('returns an operator to the operator-only onboarding route', async () => {
        render(
            <MemoryRouter>
                <PlatformAccountSupport />
            </MemoryRouter>,
        );

        expect(await screen.findByRole('heading', { name: 'Barangay Operator account support' })).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Barangay applications' })).toHaveAttribute(
            'href',
            '/operator/barangay-applications',
        );
        expect(fetchPlatformAccounts).toHaveBeenCalledWith({
            search: '',
            role: '',
            active: undefined,
            page: 1,
        });
    });
});
