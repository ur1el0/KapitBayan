import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PwaInstallPrompt } from './PwaInstallPrompt';

describe('PwaInstallPrompt', () => {
    it('shows install prompt when beforeinstallprompt event fires and handles install click', async () => {
        const promptMock = vi.fn().mockResolvedValue(undefined);
        const userChoiceMock = Promise.resolve({ outcome: 'accepted' as const });

        render(<PwaInstallPrompt />);
        expect(screen.queryByLabelText(/Install KapitBayan App/i)).not.toBeInTheDocument();

        // Simulate beforeinstallprompt event
        const event = new Event('beforeinstallprompt');
        Object.assign(event, {
            prompt: promptMock,
            userChoice: userChoiceMock,
        });

        act(() => {
            window.dispatchEvent(event);
        });

        // Prompt banner should now appear
        const installSection = screen.getByLabelText(/Install KapitBayan App/i);
        expect(installSection).toBeInTheDocument();

        // Click Install button
        const installButton = screen.getByRole('button', { name: /^Install$/i });
        await act(async () => {
            fireEvent.click(installButton);
        });

        expect(promptMock).toHaveBeenCalledTimes(1);
        expect(screen.queryByLabelText(/Install KapitBayan App/i)).not.toBeInTheDocument();
    });

    it('dismisses the prompt when the dismiss button is clicked', () => {
        const promptMock = vi.fn().mockResolvedValue(undefined);
        const userChoiceMock = Promise.resolve({ outcome: 'dismissed' as const });

        render(<PwaInstallPrompt />);

        const event = new Event('beforeinstallprompt');
        Object.assign(event, {
            prompt: promptMock,
            userChoice: userChoiceMock,
        });

        act(() => {
            window.dispatchEvent(event);
        });

        const dismissButton = screen.getByRole('button', { name: /Dismiss install prompt/i });
        fireEvent.click(dismissButton);

        expect(screen.queryByLabelText(/Install KapitBayan App/i)).not.toBeInTheDocument();
    });
});
