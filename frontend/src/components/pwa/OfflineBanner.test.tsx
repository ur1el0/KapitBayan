import { act, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { OfflineBanner } from './OfflineBanner';

describe('OfflineBanner', () => {
    beforeEach(() => {
        vi.useRealTimers();
        Object.defineProperty(navigator, 'onLine', {
            configurable: true,
            value: true,
        });
    });

    it('remains hidden when online', () => {
        render(<OfflineBanner />);
        expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    it('shows the offline banner when the window goes offline', () => {
        render(<OfflineBanner />);
        expect(screen.queryByRole('status')).not.toBeInTheDocument();

        act(() => {
            window.dispatchEvent(new Event('offline'));
        });

        const alert = screen.getByRole('status');
        expect(alert).toBeInTheDocument();
        expect(alert).toHaveTextContent(/You are currently offline/i);
    });

    it('shows reconnection notice when returning online and then dismisses it', () => {
        vi.useFakeTimers();
        render(<OfflineBanner />);

        // First offline
        act(() => {
            window.dispatchEvent(new Event('offline'));
        });
        expect(screen.getByRole('status')).toHaveTextContent(/You are currently offline/i);

        // Then back online
        act(() => {
            window.dispatchEvent(new Event('online'));
        });
        expect(screen.getByRole('status')).toHaveTextContent(/Back online/i);

        // Advance 3 seconds
        act(() => {
            vi.advanceTimersByTime(3000);
        });

        expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });
});
