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

    it('switches to Borrow Equipment tab, fills form, submits, and renders equipment slip', async () => {
        render(
            <MemoryRouter>
                <LanguageProvider>
                    <PublicKiosk />
                </LanguageProvider>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Ibabang Dupay (Lucena, Quezon)')).toBeInTheDocument();
        });

        fireEvent.change(screen.getByLabelText(/Barangay/i), { target: { value: '1' } });

        // Switch to Borrow Equipment tab
        const equipTab = screen.getByRole('tab', { name: /Borrow Equipment/i });
        expect(equipTab).toBeInTheDocument();
        fireEvent.click(equipTab);

        // Switch to Walk-In (Staff Desk PIN) and fill out borrower & verification fields
        fireEvent.click(screen.getByRole('button', { name: /Walk-In \(Staff Desk PIN\)/i }));
        fireEvent.change(screen.getByLabelText(/Full name/i), { target: { value: 'Elena Ramos' } });
        fireEvent.change(screen.getByLabelText(/Barangay Staff Kiosk PIN/i), { target: { value: '4321' } });
        fireEvent.change(screen.getByLabelText(/Contact number/i), { target: { value: '09181234567' } });
        fireEvent.change(screen.getByLabelText(/Purok \/ Address in Barangay/i), { target: { value: 'Purok 2' } });
        fireEvent.change(screen.getByLabelText(/Equipment or Facility/i), { target: { value: 'Monoblock Chairs' } });
        fireEvent.change(screen.getByLabelText(/Specific purpose & venue of borrowing/i), {
            target: { value: 'Community Gathering at Covered Court' },
        });

        fireEvent.click(screen.getByLabelText(/I have read the privacy notice and agree/i));

        // Mock response
        vi.mocked(globalThis.fetch).mockImplementation((url: string | URL | Request) => {
            const urlStr = String(url);
            if (urlStr.includes('/kiosk/equipment/')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ reference: 'EQ-000042', status: 'PENDING' }),
                } as Response);
            }
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({}),
            } as Response);
        });

        fireEvent.click(screen.getByRole('button', { name: /Submit request/i }));

        await waitFor(() => {
            expect(screen.getByText('EQ-000042')).toBeInTheDocument();
        });
        expect(screen.getByText(/Monoblock Chairs/i)).toBeInTheDocument();

        const equipmentPostCall = vi.mocked(globalThis.fetch).mock.calls.find(([url]) =>
            String(url).includes('/kiosk/equipment/'),
        );
        expect(equipmentPostCall).toBeDefined();
        const sentBody = JSON.parse(String(equipmentPostCall?.[1]?.body));
        expect(sentBody).toMatchObject({
            auth_mode: 'staff_pin',
            staff_kiosk_pin: '4321',
            walkin_name: 'Elena Ramos',
            walkin_contact: '09181234567',
            walkin_purok: 'Purok 2',
            borrower_id_type: 'Barangay ID',
        });
    });

    it('supports verified resident sign-in on Borrow Equipment tab without saving session', async () => {
        render(
            <MemoryRouter>
                <LanguageProvider>
                    <PublicKiosk />
                </LanguageProvider>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Ibabang Dupay (Lucena, Quezon)')).toBeInTheDocument();
        });

        fireEvent.change(screen.getByLabelText(/Barangay/i), { target: { value: '1' } });
        fireEvent.click(screen.getByRole('tab', { name: /Borrow Equipment/i }));

        fireEvent.change(screen.getByLabelText(/Resident username or email/i), { target: { value: 'maria_res' } });
        fireEvent.change(screen.getByLabelText(/Account password/i), { target: { value: 'ResidentPass123!' } });
        fireEvent.change(screen.getByLabelText(/Contact number/i), { target: { value: '09171234567' } });
        fireEvent.change(screen.getByLabelText(/Purok \/ Address in Barangay/i), { target: { value: 'Purok 3' } });
        fireEvent.change(screen.getByLabelText(/Specific purpose & venue of borrowing/i), {
            target: { value: 'Neighborhood assembly at Purok 3 hall' },
        });
        fireEvent.click(screen.getByLabelText(/I have read the privacy notice and agree/i));

        vi.mocked(globalThis.fetch).mockImplementation((url: string | URL | Request) => {
            if (String(url).includes('/kiosk/equipment/')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ reference: 'EQ-000077', status: 'PENDING' }),
                } as Response);
            }
            return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
        });

        fireEvent.click(screen.getByRole('button', { name: /Submit request/i }));

        await waitFor(() => {
            expect(screen.getByText('EQ-000077')).toBeInTheDocument();
        });

        const equipmentPostCall = vi.mocked(globalThis.fetch).mock.calls.find(([url]) =>
            String(url).includes('/kiosk/equipment/'),
        );
        const sentBody = JSON.parse(String(equipmentPostCall?.[1]?.body));
        expect(sentBody).toMatchObject({
            auth_mode: 'resident',
            resident_username: 'maria_res',
            resident_password: 'ResidentPass123!',
            walkin_contact: '09171234567',
            walkin_purok: 'Purok 3',
        });
    });
});
