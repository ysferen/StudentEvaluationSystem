import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Login from '../features/landing/pages/LoginPage';

const mockUseAuth = vi.fn();
const mockLogin = vi.fn();

vi.mock('../features/auth/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

describe('Login page', () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
    mockLogin.mockReset();
  });

  it('submits username and password through auth hook', async () => {
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      isAuthenticated: false,
      user: null,
    });
    mockLogin.mockResolvedValue(undefined);

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
        </Routes>
      </MemoryRouter>
    );

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText('Enter your username'), 'student');
    await user.type(screen.getByPlaceholderText('Enter your password'), 'secret');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('student', 'secret');
    });
  });

  it('redirects authenticated student to student route', async () => {
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      isAuthenticated: true,
      user: { role: 'student' },
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/student" element={<div>Student Route</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Student Route')).toBeInTheDocument();
  });

  it('redirects authenticated instructor to instructor route', async () => {
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      isAuthenticated: true,
      user: { role: 'instructor' },
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/instructor" element={<div>Instructor Route</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Instructor Route')).toBeInTheDocument();
  });

  it('redirects authenticated admin to head route', async () => {
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      isAuthenticated: true,
      user: { role: 'admin' },
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/head" element={<div>Head Route</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Head Route')).toBeInTheDocument();
  });
});
