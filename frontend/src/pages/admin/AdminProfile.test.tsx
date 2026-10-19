import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axiosPrivate } from '../../api/axios';
import { AuthContext, type AuthContextType } from '../../context/auth-context';
import { AdminProfile } from './AdminProfile';

vi.mock('../../api/axios', () => ({ axiosPrivate: { defaults: { baseURL: 'http://localhost:8000/api/v1' }, get: vi.fn(), patch: vi.fn() } }));

const updateUser = vi.fn();
const authValue: AuthContextType = {
    user: {
        id: 40,
        username: 'brightlane897@gmail.com',
        email: 'brightlane897@gmail.com',
        full_name: 'Monkey D. Luffy',
        role: 'ADMIN',
        barangay: { name: 'Cotta' },
    },
    login: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    isAuthenticated: true,
    updateBarangayPrimaryColor: vi.fn(),
    updateUser,
};

function renderProfile() {
    return render(
        <AuthContext.Provider value={authValue}>
            <AdminProfile />
        </AuthContext.Provider>,
    );
}

describe('AdminProfile', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(axiosPrivate.get).mockResolvedValue({ data: { ...authValue.user, profile_picture: null } } as never);
    });

    it('shows the full name as the profile heading and the email only in contact information', async () => {
        renderProfile();

        expect(screen.getByRole('heading', { level: 2, name: 'Monkey D. Luffy' })).toBeInTheDocument();
        expect(screen.getByText('brightlane897@gmail.com')).toBeInTheDocument();
        expect(screen.getByText('Cotta')).toBeInTheDocument();
    });

    it('uploads and displays the administrator profile picture', async () => {
        vi.mocked(axiosPrivate.patch).mockResolvedValue({
            data: { ...authValue.user, profile_picture: '/media/profile_pictures/admin.png' },
        } as never);
        renderProfile();

        const picture = new File(['profile'], 'profile.png', { type: 'image/png' });
        fireEvent.change(screen.getByLabelText('Profile picture file'), { target: { files: [picture] } });

        await waitFor(() => expect(axiosPrivate.patch).toHaveBeenCalled());
        const [url, payload] = vi.mocked(axiosPrivate.patch).mock.calls[0];
        expect(url).toBe('/auth/me/');
        expect(payload).toBeInstanceOf(FormData);
        expect((payload as FormData).get('profile_picture')).toBe(picture);
        expect(await screen.findByRole('status')).toHaveTextContent('Profile picture updated.');
        expect(await screen.findByRole('img', { name: 'Monkey D. Luffy profile picture' })).toHaveAttribute('src', 'http://localhost:8000/media/profile_pictures/admin.png');
        expect(screen.queryByText('Choose an image file up to 5 MB.')).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Remove photo' })).not.toBeInTheDocument();
    });
});
