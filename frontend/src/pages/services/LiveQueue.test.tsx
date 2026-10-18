import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import { LiveQueue } from "./LiveQueue";
import { axiosPrivate } from "../../api/axios";
import { useAuth } from "../../context/auth-context";
import { BrowserRouter } from "react-router-dom";

vi.mock('../../api/axios', () => ({
    axiosPrivate: {
        get: vi.fn(),
        post: vi.fn(),
        delete: vi.fn(),
    },
}));

vi.mock('../../context/auth-context', () => ({
    useAuth: vi.fn(),
}));

const mockTickets = [
    {
        ticket_id: 1,
        ticket_number: 'Q-001',
        service_type: 'Clearance',
        resident_name: 'Resident One',
        status: 'WAITING',
        is_priority: false,
        created_at: '2026-08-14T08:00:00Z',
    },
    {
        ticket_id: 2,
        ticket_number: 'Q-002',
        service_type: 'Permit',
        resident_name: 'Resident Two',
        status: 'SERVING',
        is_priority: false,
        created_at: '2026-08-14T08:05:00Z',
    },
];

const mockAuth = (role: string) => {
    vi.mocked(useAuth).mockReturnValue({
        user: { role },
        login: vi.fn(),
        logout: vi.fn(async () => {}),
        isAuthenticated: true,
        updateBarangayPrimaryColor: vi.fn(),
    });
};

const renderQueue = (role = 'ADMIN') => {
    mockAuth(role);
    return render(
        <BrowserRouter>
            <LiveQueue />
        </BrowserRouter>,
    );
};

class MockSpeechSynthesisUtterance {
    text: string;
    lang = '';
    rate = 1;
    volume = 1;

    constructor(text: string) {
        this.text = text;
    }
}

const mockBrowserAudio = () => {
    const speechSynthesis = {
        cancel: vi.fn(),
        speak: vi.fn(),
    };
    const oscillator = {
        type: 'sine',
        frequency: { setValueAtTime: vi.fn() },
        connect: vi.fn(),
        start: vi.fn(),
        stop: vi.fn(),
    };
    const gain = {
        gain: {
            setValueAtTime: vi.fn(),
            exponentialRampToValueAtTime: vi.fn(),
        },
        connect: vi.fn(),
    };
    const audioContext = {
        state: 'suspended',
        currentTime: 0,
        destination: {},
        resume: vi.fn(async () => {
            audioContext.state = 'running';
        }),
        createOscillator: vi.fn(() => oscillator),
        createGain: vi.fn(() => gain),
    };
    function MockAudioContextConstructor() {
        return audioContext;
    }
    const audioContextConstructor = vi.fn(MockAudioContextConstructor);

    vi.stubGlobal('speechSynthesis', speechSynthesis);
    vi.stubGlobal('SpeechSynthesisUtterance', MockSpeechSynthesisUtterance);
    vi.stubGlobal('AudioContext', audioContextConstructor);

    return { speechSynthesis, audioContext, audioContextConstructor };
};

describe('LiveQueue Component', () => {
    beforeEach(() => {
        vi.mocked(axiosPrivate.get).mockReset();
        vi.mocked(axiosPrivate.post).mockReset();
        vi.mocked(axiosPrivate.delete).mockReset();
        vi.mocked(axiosPrivate.get).mockResolvedValue({
            data: { results: mockTickets },
        } as never);
        vi.mocked(axiosPrivate.post).mockResolvedValue({ data: {} } as never);
    });

    afterEach(() => {
        cleanup();
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    it('renders queue data and does not offer a call-specific skip action', async () => {
        renderQueue();

        expect(await screen.findByText('Q-002')).toBeInTheDocument();
        expect(screen.getByText(/now serving/i)).toBeInTheDocument();
        expect(screen.getByText('Permit')).toBeInTheDocument();
        expect(screen.getByText('Waiting List')).toBeInTheDocument();
        expect(screen.getByText('Q-001')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /call q-001/i })).not.toBeInTheDocument();
    });

    it('keeps the initial queue unavailable after failure and retries into a real empty state', async () => {
        let resolveRetry!: (response: { data: { results: never[] } }) => void;
        const pendingRetry = new Promise<{ data: { results: never[] } }>((resolve) => {
            resolveRetry = resolve;
        });
        vi.mocked(axiosPrivate.get)
            .mockRejectedValueOnce(new Error('Network unavailable'))
            .mockReturnValueOnce(pendingRetry as never);

        renderQueue();

        expect(await screen.findByRole('alert')).toHaveTextContent('Failed to load queue tickets.');
        const totalWaitingCard = screen.getByText('Total Waiting').parentElement?.parentElement;
        expect(totalWaitingCard).toHaveTextContent('--');
        expect(screen.queryByText(/No .* tickets currently waiting/)).not.toBeInTheDocument();
        expect(screen.queryByText('No resident currently being served')).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

        expect(screen.getByRole('button', { name: 'Trying again…' })).toBeDisabled();
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(1, '/tickets/');
        expect(axiosPrivate.get).toHaveBeenNthCalledWith(2, '/tickets/');

        await act(async () => {
            resolveRetry({ data: { results: [] } });
            await pendingRetry;
        });

        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(screen.getByText('Total Waiting').parentElement?.parentElement).toHaveTextContent('0');
        expect(screen.getByText('No priority queue tickets currently waiting.')).toBeInTheDocument();
        expect(screen.getByText('No resident currently being served')).toBeInTheDocument();
        expect(axiosPrivate.post).not.toHaveBeenCalled();
    });

    it('preserves the last loaded queue when an automatic refresh fails', async () => {
        vi.useFakeTimers();
        renderQueue();

        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        expect(screen.getByText('Q-002')).toBeInTheDocument();
        vi.mocked(axiosPrivate.get).mockRejectedValueOnce(new Error('Network unavailable'));

        await act(async () => {
            await vi.advanceTimersByTimeAsync(3000);
        });

        expect(screen.getByRole('alert')).toHaveTextContent('Failed to load queue tickets.');
        expect(screen.getByText('Q-002')).toBeInTheDocument();
        expect(screen.getByText('Q-001')).toBeInTheDocument();
        expect(screen.getByText('Total Waiting').parentElement?.parentElement).toHaveTextContent('1');

        await act(async () => {
            await vi.advanceTimersByTimeAsync(3000);
        });

        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
        expect(screen.getByText('Q-002')).toBeInTheDocument();
    });

    it('shows priority and regular tickets in separate waiting lanes', async () => {
        vi.mocked(axiosPrivate.get).mockResolvedValueOnce({
            data: {
                results: [
                    ...mockTickets,
                    {
                        ticket_id: 3,
                        ticket_number: 'Q-003',
                        service_type: 'Residency Certificate',
                        resident_name: 'Priority Resident',
                        status: 'WAITING',
                        is_priority: true,
                        created_at: '2026-08-14T08:10:00Z',
                    },
                ],
            },
        } as never);

        renderQueue();

        await screen.findByText('Priority Resident');
        const priorityLane = screen.getByText('Priority Queue').closest('tbody');
        const regularLane = screen.getByText('Regular Queue').closest('tbody');
        const priorityResident = screen.getByText('Priority Resident').closest('tr');
        const regularResident = screen.getByText('Resident One').closest('tr');

        expect(priorityLane).not.toBeNull();
        expect(regularLane).not.toBeNull();
        expect(priorityLane).toContainElement(priorityResident);
        expect(regularLane).toContainElement(regularResident);
        expect(priorityLane!.compareDocumentPosition(regularLane!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it('requires an admin-entered reason and uses the audited priority endpoint', async () => {
        renderQueue('ADMIN');

        fireEvent.click(await screen.findByRole('button', { name: 'Grant priority for Q-001' }));
        fireEvent.change(screen.getByLabelText(/reason for granting priority/i), {
            target: { value: 'Eligibility checked at the service desk.' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Save priority change' }));

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith('/tickets/1/priority/', {
                priority_status: 'priority',
                reason: 'Eligibility checked at the service desk.',
            });
        });
    });

    it('does not show priority assignment controls to a field official', async () => {
        renderQueue('FIELD_OFFICIAL');

        expect(await screen.findByText('Q-001')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /grant priority/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /remove priority/i })).not.toBeInTheDocument();
    });

    it('advances through the server queue-order endpoint', async () => {
        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({
            data: { current_ticket: 'Q-001' },
        } as never);
        renderQueue('FIELD_OFFICIAL');

        fireEvent.click(await screen.findByRole('button', { name: /next queue/i }));

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith('/tickets/next/');
            expect(screen.getByText('Now serving ticket Q-001')).toBeInTheDocument();
        });
    });

    it('marks the serving ticket complete using its server endpoint', async () => {
        renderQueue('FIELD_OFFICIAL');

        await screen.findByText('Q-002');
        fireEvent.click(screen.getByRole('button', { name: 'Mark as Done' }));

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith('/tickets/2/complete/');
        });
    });

    it('pages the resident linked to the serving ticket through the API', async () => {
        vi.mocked(axiosPrivate.post).mockResolvedValueOnce({
            data: { detail: 'Paging notification accepted for delivery.' },
        } as never);
        renderQueue();

        await screen.findByText('Q-002');
        fireEvent.click(screen.getByRole('button', { name: 'Page resident' }));

        await waitFor(() => {
            expect(axiosPrivate.post).toHaveBeenCalledWith('/tickets/2/notify/');
        });
    });

    it('opens queue history, deletes a ticket, and closes the modal', async () => {
        vi.spyOn(window, 'confirm').mockReturnValue(true);
        vi.mocked(axiosPrivate.delete).mockResolvedValueOnce({ data: {} } as never);
        renderQueue();

        await screen.findByText('Q-002');
        fireEvent.click(screen.getByRole('button', { name: 'Queue History' }));

        const history = screen.getByRole('dialog', { name: 'Queue Activity History' });
        expect(history).toHaveTextContent('Q-001');
        fireEvent.click(within(history).getAllByRole('button', { name: 'Delete' })[0]);

        await waitFor(() => {
            expect(window.confirm).toHaveBeenCalledWith(
                'Are you sure you want to permanently delete this queue record?',
            );
            expect(axiosPrivate.delete).toHaveBeenCalledWith('/tickets/1/');
        });

        fireEvent.click(screen.getByRole('button', { name: 'Close queue history' }));
        expect(screen.queryByRole('dialog', { name: 'Queue Activity History' })).not.toBeInTheDocument();
    });

    it('polls tickets every three seconds and clears the interval on unmount', async () => {
        vi.useFakeTimers();
        renderQueue();

        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });
        expect(axiosPrivate.get).toHaveBeenCalledTimes(1);

        await act(async () => {
            await vi.advanceTimersByTimeAsync(3000);
        });
        expect(axiosPrivate.get).toHaveBeenCalledTimes(2);

        cleanup();
        await act(async () => {
            await vi.advanceTimersByTimeAsync(3000);
        });
        expect(axiosPrivate.get).toHaveBeenCalledTimes(2);
    });

    it('unlocks speech and audio from the announcer control without announcing the initial ticket', async () => {
        const audio = mockBrowserAudio();
        renderQueue();

        expect(await screen.findByText('Q-002')).toBeInTheDocument();
        expect(audio.speechSynthesis.speak).not.toHaveBeenCalled();

        fireEvent.click(screen.getByTitle('Enable Announcer'));

        expect(audio.audioContextConstructor).toHaveBeenCalledOnce();
        expect(audio.audioContext.resume).toHaveBeenCalledOnce();
        expect(audio.speechSynthesis.speak).toHaveBeenCalledOnce();
        expect(audio.speechSynthesis.speak.mock.calls[0][0].text).toBe(
            'Audio announcements enabled.',
        );
    });

    it('announces the first serving ticket after the queue transitions from idle', async () => {
        vi.useFakeTimers();
        const audio = mockBrowserAudio();
        const waitingTickets = [mockTickets[0]];
        const servingTickets = [
            { ...mockTickets[0], status: 'SERVING' },
        ];
        vi.mocked(axiosPrivate.get)
            .mockReset()
            .mockResolvedValueOnce({ data: { results: waitingTickets } } as never)
            .mockResolvedValueOnce({ data: { results: servingTickets } } as never);

        renderQueue();
        await act(async () => {
            await Promise.resolve();
            await Promise.resolve();
        });

        fireEvent.click(screen.getByTitle('Enable Announcer'));
        audio.speechSynthesis.speak.mockClear();

        await act(async () => {
            await vi.advanceTimersByTimeAsync(3000);
        });

        expect(axiosPrivate.get).toHaveBeenCalledTimes(2);
        expect(audio.speechSynthesis.speak).toHaveBeenCalledOnce();
        expect(audio.speechSynthesis.speak.mock.calls[0][0].text).toBe(
            'Now serving ticket Q-001. Please proceed to the service counter.',
        );
    });
});
