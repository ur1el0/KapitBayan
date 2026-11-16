import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { PublicKiosk } from './PublicKiosk';
import { LanguageProvider } from '../../context/language-context';

describe('PublicKiosk Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        globalThis.fetch = vi.fn().mockImplementation((url: string) => {
            if (url.includes('/public/barangays/')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([
                        { id: 1, name: 'Ibabang Dupay', municipality: 'Lucena', province: 'Quezon' },
                    ]),
                });
            }
            if (url.includes('/kiosk/queue/')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ reference: 'Q-00101', status: 'WAITING' }),
                });
            }
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({}),
            });
        });
    });

    it('renders the kiosk form, submits a walk-in queue request, and verifies print slip structure', async () => {
        const printSpy = vi.spyOn(window, 'print').mockImplementation(() => {});

        render(
            <MemoryRouter>
                <LanguageProvider>
                    <PublicKiosk />
                </LanguageProvider>
            </MemoryRouter>
        );

        // Heading is visible
        expect(screen.getByText('Barangay Public Service Kiosk')).toBeInTheDocument();
        expect(screen.getByText('Public walk-in mode')).toBeInTheDocument();

        // Select barangay
        await waitFor(() => {
            expect(screen.getByText('Ibabang Dupay (Lucena, Quezon)')).toBeInTheDocument();
        });

        const selectBarangay = screen.getByLabelText(/Barangay/i);
        fireEvent.change(selectBarangay, { target: { value: '1' } });

        // Fill out walk-in name
        const nameInput = screen.getByLabelText(/Full name/i);
        fireEvent.change(nameInput, { target: { value: 'Juan Dela Cruz' } });

        // Check privacy acknowledgement
        const privacyCheckbox = screen.getByLabelText(/I have read the privacy notice and agree/i);
        fireEvent.click(privacyCheckbox);

        // Submit form
        const submitButton = screen.getByRole('button', { name: /Submit request/i });
        fireEvent.click(submitButton);

        // Printable slip should appear with reference number
        await waitFor(() => {
            expect(screen.getByText('Q-00101')).toBeInTheDocument();
        });

        // Verify the printable slip container has the .kiosk-print-slip class
        const slipContainer = screen.getByRole('status');
        expect(slipContainer).toHaveClass('kiosk-print-slip');

        // Check that Print Slip button exists and triggers window.print
        const printButton = screen.getByRole('button', { name: /Print Walk-in Ticket Slip/i });
        expect(printButton).toBeInTheDocument();

        fireEvent.click(printButton);
        expect(printSpy).toHaveBeenCalledTimes(1);

        printSpy.mockRestore();
    });
});
