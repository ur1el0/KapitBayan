import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axiosPrivate } from '../../api/axios';
import { DocumentRequests } from './DocumentRequests';

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        post: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
    },
}));

vi.mock('react-hot-toast', () => ({
    default: { error: vi.fn(), success: vi.fn() },
}));

const request = {
    id: 7,
    requester_name: 'Rosa Resident',
    purok: 'Purok 3',
    document_type: 'Barangay Clearance',
    purpose: 'Employment requirement',
    status: 'PENDING',
    created_at: '2026-10-12T08:00:00Z',
};

describe('DocumentRequests', () => {
    beforeEach(() => {
        vi.mocked(axiosPrivate.get).mockReset();
        vi.mocked(axiosPrivate.post).mockReset();
        vi.mocked(axiosPrivate.patch).mockReset();
        vi.mocked(axiosPrivate.delete).mockReset();
        vi.mocked(axiosPrivate.get).mockResolvedValue({ data: [] } as never);
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('shows an accessible list error and keeps the heading, table, and walk-in action available', async () => {
        vi.mocked(axiosPrivate.get).mockRejectedValueOnce(new Error('Network unavailable'));

        render(<DocumentRequests />);

        expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't load document requests.");
        expect(screen.getByRole('heading', { name: 'Clearance Desk & Document Requests' })).toBeInTheDocument();
        expect(screen.getByRole('columnheader', { name: 'Applicant' })).toBeInTheDocument();
        expect(screen.queryByText('No clearance requests recorded yet.')).not.toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: /request walk-in/i }));
        expect(screen.getByRole('dialog', { name: 'Create Walk-in Request' })).toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenCalledExactlyOnceWith('/document-requests/');
        expect(axiosPrivate.post).not.toHaveBeenCalled();
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('retries only the list GET after repeated failure and renders requests after recovery', async () => {
        vi.mocked(axiosPrivate.get)
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockResolvedValueOnce({ data: { results: [request] } } as never);

        render(<DocumentRequests />);
        expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't load document requests.");

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
        await waitFor(() => expect(axiosPrivate.get).toHaveBeenCalledTimes(2));
        expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't load document requests.");

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
        expect(await screen.findByText('Rosa Resident')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(screen.queryByText('No clearance requests recorded yet.')).not.toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(1, '/document-requests/');
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(2, '/document-requests/');
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(3, '/document-requests/');
        expect(axiosPrivate.post).not.toHaveBeenCalled();
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('preserves loaded requests when the post-create list refresh fails', async () => {
        vi.mocked(axiosPrivate.get)
            .mockResolvedValueOnce({ data: [request] } as never)
            .mockRejectedValueOnce(new Error('Network unavailable'));
        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({ data: {} } as never);

        render(<DocumentRequests />);
        expect(await screen.findByText('Rosa Resident')).toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: /request walk-in/i }));
        fireEvent.change(screen.getByLabelText('Resident Full Name *'), { target: { value: 'Lina Visitor' } });
        fireEvent.change(screen.getByLabelText('Other document name *'), { target: { value: 'Barangay Clearance' } });
        fireEvent.change(screen.getByLabelText('Purpose Statement *'), { target: { value: 'Proof of employment' } });
        fireEvent.click(screen.getByRole('button', { name: 'Record Walk-in Request' }));

        await waitFor(() => expect(axiosPrivate.get).toHaveBeenCalledTimes(2));
        expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't load document requests.");
        expect(screen.getByText('Rosa Resident')).toBeInTheDocument();
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        expect(axiosPrivate.post).toHaveBeenCalledExactlyOnceWith('/document-requests/', {
            walkin_name: 'Lina Visitor',
            walkin_purok: '',
            document_type: 'Barangay Clearance',
            purpose: 'Proof of employment',
        });
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });

    it('shows the genuine empty state after a retry successfully returns no requests', async () => {
        vi.mocked(axiosPrivate.get)
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockResolvedValueOnce({ data: { results: [] } } as never);

        render(<DocumentRequests />);
        await screen.findByRole('alert');
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(await screen.findByText('No clearance requests recorded yet.')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(2);
    });

    it('disables retry while the GET is pending without issuing mutations', async () => {
        vi.mocked(axiosPrivate.get)
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockImplementationOnce(() => new Promise(() => {}));

        render(<DocumentRequests />);
        await screen.findByRole('alert');
        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(await screen.findByRole('button', { name: 'Trying again…' })).toBeDisabled();
        expect(screen.getByRole('button', { name: /request walk-in/i })).toBeEnabled();
        expect(axiosPrivate.get).toHaveBeenCalledTimes(2);
        expect(axiosPrivate.post).not.toHaveBeenCalled();
        expect(axiosPrivate.patch).not.toHaveBeenCalled();
        expect(axiosPrivate.delete).not.toHaveBeenCalled();
    });
});
