import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ResidentHelp } from './ResidentHelp';
import { axiosPrivate } from '../../api/axios';

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
    },
}));

describe('ResidentHelp', () => {
    beforeEach(() => {
        vi.mocked(axiosPrivate.get).mockReset();
    });

    it('renders FAQs and emergency hotlines with clickable telephone links', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation((url) => {
            if (url === '/faqs/') {
                return Promise.resolve({
                    data: {
                        results: [
                            {
                                id: 1,
                                question: 'How do I request a clearance?',
                                answer: 'Submit a request through the Documents tab.',
                                order: 1,
                                audience: 'RESIDENT',
                                category: 'DOCUMENTS',
                            },
                        ],
                    },
                } as never);
            }
            if (url === '/hotlines/') {
                return Promise.resolve({
                    data: {
                        results: [
                            {
                                id: 101,
                                name: 'Barangay Tanod Response',
                                number: '0912-345-6789',
                                category: 'BARANGAY',
                                category_display: 'Barangay Desk',
                                is_active: true,
                            },
                        ],
                    },
                } as never);
            }
            return Promise.resolve({ data: [] } as never);
        });

        render(
            <MemoryRouter>
                <ResidentHelp />
            </MemoryRouter>
        );

        // Emergency hotlines section
        expect(await screen.findByRole('heading', { name: /Emergency Hotlines/i })).toBeInTheDocument();
        expect(screen.getByText('Barangay Tanod Response')).toBeInTheDocument();
        expect(screen.getByText('0912-345-6789')).toBeInTheDocument();

        // Direct tel: action button
        const callLink = screen.getByRole('link', { name: /Call Barangay Tanod Response at 0912-345-6789/i });
        expect(callLink).toHaveAttribute('href', 'tel:0912-345-6789');

        // National 911 fallback link
        const nationalLink = screen.getByRole('link', { name: /National Emergency: 911/i });
        expect(nationalLink).toHaveAttribute('href', 'tel:911');

        // FAQs section
        expect(await screen.findByText('How do I request a clearance?')).toBeInTheDocument();
    });

    it('handles empty hotlines and failed FAQs gracefully', async () => {
        vi.mocked(axiosPrivate.get).mockImplementation((url) => {
            if (url === '/faqs/') {
                return Promise.reject(new Error('Network error'));
            }
            if (url === '/hotlines/') {
                return Promise.resolve({ data: [] } as never);
            }
            return Promise.resolve({ data: [] } as never);
        });

        render(
            <MemoryRouter>
                <ResidentHelp />
            </MemoryRouter>
        );

        // Hotline fallback
        expect(await screen.findByText('No Barangay-specific hotlines published yet.')).toBeInTheDocument();

        // FAQ error
        expect(await screen.findByRole('alert')).toHaveTextContent('Help could not be loaded.');
    });
});
