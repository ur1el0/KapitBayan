import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { useAuth } from '../../context/auth-context';
import { EquipmentBorrowing } from './EquipmentBorrowing';

vi.mock('../../api/axios', () => ({
    axiosPrivate: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}));
vi.mock('../../context/auth-context', () => ({ useAuth: vi.fn() }));

const formatOffsetDate = (daysFromToday: number): string => {
    const date = new Date(Date.now() - new Date().getTimezoneOffset() * 60000);
    date.setUTCDate(date.getUTCDate() + daysFromToday);
    return date.toISOString().split('T')[0];
};

describe('EquipmentBorrowing', () => {
    beforeEach(() => {
        vi.mocked(axiosPrivate.get).mockReset();
        vi.mocked(axiosPrivate.post).mockReset();
        vi.mocked(axiosPrivate.patch).mockReset();
        vi.mocked(axiosPrivate.get).mockResolvedValue({ data: [] } as never);
    });

    it('opens the modal, validates dates, and submits a resident borrowing request', async () => {
        const borrowDate = formatOffsetDate(4);
        const invalidReturnDate = formatOffsetDate(2);
        const validReturnDate = formatOffsetDate(5);

        vi.mocked(useAuth).mockReturnValue({ user: { role: 'RESIDENT' } } as never);
        vi.mocked(axiosPrivate.post).mockResolvedValue({ data: {} } as never);

        render(<EquipmentBorrowing />);
        fireEvent.click(await screen.findByRole('button', { name: 'Request Equipment or Facility' }));

        expect(screen.getByRole('dialog')).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText('Item or facility'), {
            target: { value: 'Tent / Canopy' },
        });
        fireEvent.change(screen.getByLabelText('Quantity'), {
            target: { value: '2' },
        });
        fireEvent.change(screen.getByLabelText('Borrow date'), {
            target: { value: borrowDate },
        });
        fireEvent.change(screen.getByLabelText('Return date'), {
            target: { value: invalidReturnDate },
        });
        fireEvent.change(screen.getByLabelText('Purpose'), {
            target: { value: 'Community health assembly.' },
        });

        fireEvent.click(screen.getByRole('button', { name: 'Submit Borrowing Request' }));
        expect(await screen.findByRole('alert')).toHaveTextContent(
            'Return date must be on or after the borrow date.',
        );
        expect(axiosPrivate.post).not.toHaveBeenCalled();

        fireEvent.change(screen.getByLabelText('Return date'), {
            target: { value: validReturnDate },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Submit Borrowing Request' }));

        await waitFor(() =>
            expect(axiosPrivate.post).toHaveBeenCalledWith('/equipment-requests/', {
                item_type: 'Tent / Canopy',
                quantity: 2,
                borrow_date: borrowDate,
                return_date: validReturnDate,
                time_slot: '08:00 AM - 05:00 PM',
                purpose: 'Community health assembly.',
            }),
        );
    });

    it('shows InlineErrorState on load failure and recovers on retry', async () => {
        vi.mocked(useAuth).mockReturnValue({ user: { role: 'RESIDENT' } } as never);
        vi.mocked(axiosPrivate.get)
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockResolvedValueOnce({
                data: [
                    {
                        id: 4,
                        resident_name: 'Maria Santos',
                        item_type: 'Monoblock Chairs',
                        quantity: 30,
                        borrow_date: '2026-11-20',
                        return_date: '2026-11-21',
                        time_slot: '08:00 AM - 05:00 PM',
                        purpose: 'Family gathering.',
                        status: 'PENDING',
                        admin_notes: '',
                        created_at: '2026-11-16T00:00:00Z',
                    },
                ],
            } as never);

        render(<EquipmentBorrowing />);
        expect(await screen.findByRole('alert')).toHaveTextContent(
            "We couldn't load equipment borrowing requests.",
        );

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
        expect(await screen.findByText('Family gathering.')).toBeInTheDocument();
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('allows admin to filter, require a decline reason, approve, and mark returned', async () => {
        vi.mocked(useAuth).mockReturnValue({ user: { role: 'ADMIN' } } as never);
        vi.mocked(axiosPrivate.get).mockResolvedValue({
            data: [
                {
                    id: 10,
                    resident_name: 'Juan Dela Cruz',
                    item_type: 'Sound System',
                    quantity: 1,
                    borrow_date: '2026-11-22',
                    return_date: '2026-11-22',
                    time_slot: '09:00 AM - 12:00 PM',
                    purpose: 'Youth seminar.',
                    status: 'PENDING',
                    admin_notes: '',
                    created_at: '2026-11-16T00:00:00Z',
                },
            ],
        } as never);

        render(<EquipmentBorrowing />);
        const declineBtn = await screen.findByRole('button', { name: 'Decline' });
        fireEvent.click(declineBtn);
        expect(axiosPrivate.patch).not.toHaveBeenCalled();

        vi.mocked(axiosPrivate.patch).mockResolvedValueOnce({
            data: {
                id: 10,
                resident_name: 'Juan Dela Cruz',
                item_type: 'Sound System',
                quantity: 1,
                borrow_date: '2026-11-22',
                return_date: '2026-11-22',
                time_slot: '09:00 AM - 12:00 PM',
                purpose: 'Youth seminar.',
                status: 'APPROVED',
                admin_notes: 'Approved for morning use.',
                created_at: '2026-11-16T00:00:00Z',
            },
        } as never);

        fireEvent.change(screen.getByLabelText('Admin remarks'), {
            target: { value: 'Approved for morning use.' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Approve' }));

        await waitFor(() =>
            expect(axiosPrivate.patch).toHaveBeenCalledWith('/equipment-requests/10/', {
                status: 'APPROVED',
                admin_notes: 'Approved for morning use.',
            }),
        );

        const markReturnedBtn = await screen.findByRole('button', { name: 'Mark Returned' });
        vi.mocked(axiosPrivate.patch).mockResolvedValueOnce({
            data: {
                id: 10,
                resident_name: 'Juan Dela Cruz',
                item_type: 'Sound System',
                quantity: 1,
                borrow_date: '2026-11-22',
                return_date: '2026-11-22',
                time_slot: '09:00 AM - 12:00 PM',
                purpose: 'Youth seminar.',
                status: 'RETURNED',
                admin_notes: 'Returned complete.',
                created_at: '2026-11-16T00:00:00Z',
            },
        } as never);

        fireEvent.change(screen.getByLabelText('Admin remarks'), {
            target: { value: 'Returned complete.' },
        });
        fireEvent.click(markReturnedBtn);

        await waitFor(() =>
            expect(axiosPrivate.patch).toHaveBeenCalledWith('/equipment-requests/10/', {
                status: 'RETURNED',
                admin_notes: 'Returned complete.',
            }),
        );
    });
});
