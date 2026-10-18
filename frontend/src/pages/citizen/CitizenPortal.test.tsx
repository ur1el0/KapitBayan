import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CitizenDocuments } from './CitizenDocuments';
import { CitizenLayout } from '../../components/layout/CitizenLayout';
import { AuthProvider } from '../../context/AuthContext';
import { axiosPrivate } from '../../api/axios';
import { CitizenQueue } from './CitizenQueue';

// Mock axiosPrivate
vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        post: vi.fn(),
        delete: vi.fn(),
    },
}));

describe('Resident Portal Components', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders CitizenLayout header with navigation tabs and branding', () => {
        render(
            <BrowserRouter>
                <AuthProvider restoreSession={false}>
                    <CitizenLayout />
                </AuthProvider>
            </BrowserRouter>
        );

        // Verify brand and navigation tabs
        expect(screen.getByText('Resident Portal')).toBeInTheDocument();
        expect(screen.getAllByText('Documents & Clearances')[0]).toBeInTheDocument();
        expect(screen.getAllByText('Live Queue Ticker')[0]).toBeInTheDocument();
        expect(screen.getAllByText('Community Bulletin')[0]).toBeInTheDocument();
    });

    it('renders empty state when citizen has no active document requests', async () => {
        vi.mocked(axiosPrivate.get)
            .mockResolvedValueOnce({ data: { results: [] } })
            .mockResolvedValueOnce({ data: [] });

        render(
            <BrowserRouter>
                <AuthProvider restoreSession={false}>
                    <CitizenDocuments />
                </AuthProvider>
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('No active document requests')).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /request new clearance/i })).toBeInTheDocument();
        });
    });

    it('shows a document load error instead of an empty state and retries', async () => {
        const documentResponses = vi.fn()
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockResolvedValueOnce({ data: { results: [] } });
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url === '/document-requests/') {
                return documentResponses();
            }
            if (url === '/payment-recipients/') {
                return Promise.resolve({ data: { results: [] } });
            }
            return Promise.reject(new Error(`Unhandled GET url: ${url}`));
        });

        render(
            <BrowserRouter>
                <AuthProvider restoreSession={false}>
                    <CitizenDocuments />
                </AuthProvider>
            </BrowserRouter>
        );

        expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't load your document requests.");
        expect(screen.queryByText('No active document requests')).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        await waitFor(() => {
            expect(screen.getByText('No active document requests')).toBeInTheDocument();
        });
    });

    it('renders list of active clearance requests when data is returned', async () => {
        const mockRequests = [
            {
                id: 101,
                document_type: 'Barangay Clearance',
                purpose: 'Local Employment Application',
                status: 'READY_FOR_PICKUP',
                admin_notes: 'Ready at Counter 2',
                created_at: '2026-09-06T10:00:00Z',
            },
        ];

        vi.mocked(axiosPrivate.get)
            .mockResolvedValueOnce({ data: { results: mockRequests } })
            .mockResolvedValueOnce({ data: [] });

        render(
            <BrowserRouter>
                <AuthProvider restoreSession={false}>
                    <CitizenDocuments />
                </AuthProvider>
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Barangay Clearance')).toBeInTheDocument();
            expect(screen.getByText('Local Employment Application')).toBeInTheDocument();
            expect(screen.getByText('Ready / Released')).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /download pdf/i })).toBeInTheDocument();
        });
    });
    it('renders cancel button for pending clearance and cancels upon confirmation', async () => {
        const mockRequests = [
            {
                id: 202,
                document_type: 'Certificate of Residency',
                purpose: 'Bank Account Opening',
                status: 'PENDING',
                created_at: '2026-09-06T10:00:00Z',
            },
        ];

        vi.mocked(axiosPrivate.get)
            .mockResolvedValueOnce({ data: { results: mockRequests } })
            .mockResolvedValueOnce({ data: [] })
            .mockResolvedValueOnce({ data: { results: [] } });
        vi.mocked(axiosPrivate.delete).mockResolvedValueOnce({ data: {} });
        vi.spyOn(window, 'confirm').mockReturnValue(true);

        render(
            <BrowserRouter>
                <AuthProvider restoreSession={false}>
                    <CitizenDocuments />
                </AuthProvider>
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Certificate of Residency')).toBeInTheDocument();
            expect(screen.getByText('Pending Review')).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /cancel clearance request #202/i })).toBeInTheDocument();
        });

        fireEvent.click(screen.getByRole('button', { name: /cancel clearance request #202/i }));

        await waitFor(() => {
            expect(axiosPrivate.delete).toHaveBeenCalledWith('/document-requests/202/');
            expect(screen.queryByText('Certificate of Residency')).not.toBeInTheDocument();
        });
    });
    it('renders active waiting ticket and leaves queue upon cancellation', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation((url: string) => {
            if (url === '/tickets/live-status/') {
                return Promise.resolve({
                    data: { current_ticket: 'T005', total_waiting: 3, avg_wait_mins: 6 }
                });
            }
            if (url === '/tickets/') {
                return Promise.resolve({
                    data: {
                        results: [
                            {
                                ticket_id: 77,
                                ticket_number: 'T008',
                                service_type: 'Barangay Clearance',
                                status: 'WAITING',
                                is_priority: false,
                                created_at: '2026-09-06T10:30:00Z',
                            }
                        ]
                    }
                });
            }
            return Promise.reject(new Error(`Unhandled GET url: ${url}`));
        });

        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({ data: { detail: 'Queue ticket cancelled successfully.' } });
        vi.spyOn(window, 'confirm').mockReturnValue(true);

        render(
            <BrowserRouter>
                <AuthProvider restoreSession={false}>
                    <CitizenQueue />
                </AuthProvider>
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('T008')).toBeInTheDocument();
            expect(screen.getByText('Waiting for your turn')).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /leave queue and cancel ticket/i })).toBeInTheDocument();
        });

        fireEvent.click(screen.getByRole('button', { name: /leave queue and cancel ticket/i }));

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith('/tickets/77/cancel/');
        });
    });
});
