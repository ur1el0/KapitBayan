import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { ResidentsHub } from './ResidentsHub';

vi.mock('./ResidentsManagement', () => ({
    ResidentsManagement: () => <div>Residents directory</div>,
}));

vi.mock('./ResidentVerification', () => ({
    default: ({ onManualRefreshCount }: { onManualRefreshCount?: () => void }) => (
        <div>
            Resident verification list
            <button type="button" onClick={onManualRefreshCount}>Refresh pending resident count</button>
        </div>
    ),
}));

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
    },
}));

const CurrentSearch = () => <output data-testid="current-search">{useLocation().search}</output>;

describe('ResidentsHub pending verification count', () => {
    beforeEach(() => {
        vi.mocked(axiosPrivate.get).mockReset();
    });

    it('keeps both resident views reachable and exposes the selected view state', async () => {
        vi.mocked(axiosPrivate.get).mockResolvedValue({ data: { results: [] } } as never);

        render(
            <MemoryRouter initialEntries={['/residents?keep=1&residentSearch=Juan&residentPage=2']}>
                <ResidentsHub />
                <CurrentSearch />
            </MemoryRouter>,
        );

        const views = within(screen.getByRole('navigation', { name: 'Resident views' }));
        const directoryButton = views.getByRole('button', { name: /Residents Directory & RBI/ });
        const verificationButton = views.getByRole('button', { name: /Resident Verifications/ });

        expect(directoryButton).toHaveAttribute('aria-pressed', 'true');
        expect(verificationButton).toHaveAttribute('aria-pressed', 'false');

        fireEvent.click(verificationButton);

        expect(await screen.findByText('Resident verification list')).toBeInTheDocument();
        expect(directoryButton).toHaveAttribute('aria-pressed', 'false');
        expect(verificationButton).toHaveAttribute('aria-pressed', 'true');
        let params = new URLSearchParams(screen.getByTestId('current-search').textContent ?? '');
        expect(params.get('keep')).toBe('1');
        expect(params.get('residentSearch')).toBe('Juan');
        expect(params.get('residentPage')).toBe('2');
        expect(params.get('tab')).toBe('verifications');

        fireEvent.click(directoryButton);
        expect(await screen.findByText('Residents directory')).toBeInTheDocument();
        params = new URLSearchParams(screen.getByTestId('current-search').textContent ?? '');
        expect(params.get('residentSearch')).toBe('Juan');
        expect(params.get('residentPage')).toBe('2');
        expect(params.get('tab')).toBe('directory');
    });

    it('keeps automatic count loading quiet and announces a manual refresh', async () => {
        let resolveInitialRequest!: (value: { data: { results: { id: number }[] } }) => void;
        let resolveManualRefresh!: (value: { data: { results: { id: number }[] } }) => void;
        vi.mocked(axiosPrivate.get).mockImplementationOnce(
            () => new Promise((resolve) => { resolveInitialRequest = resolve; }),
        ).mockImplementationOnce(
            () => new Promise((resolve) => { resolveManualRefresh = resolve; }),
        );

        render(
            <MemoryRouter>
                <ResidentsHub />
            </MemoryRouter>,
        );

        expect(screen.queryByRole('status')).not.toBeInTheDocument();
        expect(screen.queryByLabelText(/pending resident verifications/i)).not.toBeInTheDocument();

        await act(async () => {
            resolveInitialRequest({ data: { results: [{ id: 1 }, { id: 2 }] } });
        });

        expect(await screen.findByLabelText('2 pending resident verifications')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: /Resident Verifications/ }));
        fireEvent.click(await screen.findByRole('button', { name: 'Refresh pending resident count' }));

        expect(screen.getByRole('status')).toHaveTextContent('Loading pending resident count');
        await act(async () => {
            resolveManualRefresh({ data: { results: [{ id: 1 }, { id: 2 }, { id: 3 }] } });
        });

        expect(await screen.findByLabelText('3 pending resident verifications')).toBeInTheDocument();
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(2);
        expect(vi.mocked(axiosPrivate.get).mock.calls).toEqual([
            ['/auth/pending-residents/'],
            ['/auth/pending-residents/'],
        ]);
    });

    it('keeps failures retryable and does not show a false zero count', async () => {
        let rejectRetry!: (reason: Error) => void;
        vi.mocked(axiosPrivate.get)
            .mockRejectedValueOnce(new Error('offline'))
            .mockImplementationOnce(
                () => new Promise((_resolve, reject) => { rejectRetry = reject; }),
            )
            .mockResolvedValueOnce({ data: { results: [{ id: 1 }] } } as never);

        render(
            <MemoryRouter>
                <ResidentsHub />
            </MemoryRouter>,
        );

        expect(await screen.findByRole('alert')).toHaveTextContent(
            "Pending resident count couldn't be loaded.",
        );
        expect(screen.queryByLabelText(/pending resident verifications/i)).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Retry pending resident count' }));
        const pendingRetry = screen.getByRole('button', { name: 'Retry pending resident count' });
        await waitFor(() => expect(pendingRetry).toBeDisabled());
        expect(pendingRetry).toHaveClass('min-h-[44px]', 'min-w-[44px]', 'focus-visible:ring-2');
        expect(screen.getByRole('status')).toHaveTextContent('Retrying pending resident count');

        await act(async () => {
            rejectRetry(new Error('offline again'));
        });

        expect(await screen.findByRole('alert')).toHaveTextContent(
            "Pending resident count couldn't be loaded.",
        );
        const secondRetry = screen.getByRole('button', { name: 'Retry pending resident count' });
        expect(secondRetry).toBeEnabled();

        fireEvent.click(secondRetry);

        expect(await screen.findByLabelText('1 pending resident verifications')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(3);
        expect(vi.mocked(axiosPrivate.get).mock.calls).toEqual([
            ['/auth/pending-residents/'],
            ['/auth/pending-residents/'],
            ['/auth/pending-residents/'],
        ]);
    });

    it('treats a successful empty response as a genuine zero without showing an error', async () => {
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({ data: { results: [] } } as never);

        render(
            <MemoryRouter>
                <ResidentsHub />
            </MemoryRouter>,
        );

        await waitFor(() => expect(axiosPrivate.get).toHaveBeenCalledOnce());
        expect(screen.queryByLabelText(/pending resident verifications/i)).not.toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('treats a malformed count response as unavailable instead of zero', async () => {
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({ data: { results: 'invalid' } } as never);

        render(
            <MemoryRouter>
                <ResidentsHub />
            </MemoryRouter>,
        );

        expect(await screen.findByRole('alert')).toHaveTextContent(
            "Pending resident count couldn't be loaded.",
        );
        expect(screen.queryByLabelText(/pending resident verifications/i)).not.toBeInTheDocument();
    });
});
