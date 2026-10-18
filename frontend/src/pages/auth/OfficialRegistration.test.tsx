import { fireEvent, render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { OfficialRegistration } from './OfficialRegistration';
import { axiosPublic } from '../../api/axios';
import { afterEach, beforeEach, vi } from 'vitest';

beforeEach(() => {
    vi.spyOn(axiosPublic, 'get').mockResolvedValue({ data: [{ id: 8, name: 'Barangay Ibabang Dupay', municipality: 'Lucena City', province: 'Quezon' }] } as never);
});

afterEach(() => vi.restoreAllMocks());

describe('OfficialRegistration', () => {
    it('submits an official account request for an existing barangay', async () => {
        const postSpy = vi.spyOn(axiosPublic, 'post').mockResolvedValue({ data: { id: 1 } } as never);
        render(
            <BrowserRouter>
                <OfficialRegistration />
            </BrowserRouter>,
        );

        expect(screen.getByRole('heading', { level: 2, name: 'Official Registration' })).toBeInTheDocument();
        expect(await screen.findByRole('option', { name: /Barangay Ibabang Dupay/ })).toBeInTheDocument();
        expect(screen.queryByRole('link', { name: 'Apply for Barangay Onboarding' })).not.toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Switch to Resident Sign Up' })).toHaveAttribute('href', '/register');
        expect(screen.getByRole('link', { name: 'Log in here' })).toHaveAttribute('href', '/login');

        fireEvent.change(screen.getByRole('combobox'), { target: { value: '8' } });
        fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Juan Dela Cruz' } });
        fireEvent.change(screen.getByLabelText('Official position'), { target: { value: 'Barangay Secretary' } });
        fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'juan@example.com' } });
        fireEvent.change(screen.getByLabelText('Contact number'), { target: { value: '09171234567' } });
        fireEvent.click(screen.getByRole('button', { name: 'Submit Official Account Request' }));
        expect(await screen.findByRole('status')).toHaveTextContent('Request submitted for review');
        expect(postSpy).toHaveBeenCalledWith('/auth/barangay-applications/', expect.objectContaining({
            application_type: 'OFFICIAL',
            barangay_id: 8,
            applicant_email: 'juan@example.com',
        }));
    });
});
