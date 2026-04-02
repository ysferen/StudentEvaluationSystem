import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen } from '@testing-library/react';

import Dashboard from '../features/dashboard/pages/Dashboard';

const mockUseAuth = vi.fn();

vi.mock('../features/auth/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

describe('Dashboard role routing', () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
  });

  it('shows guest dashboard when there is no user', async () => {
    mockUseAuth.mockReturnValue({ user: null });

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Welcome to Student Evaluation System')).toBeInTheDocument();
  });

  it('redirects student user to student dashboard', async () => {
    mockUseAuth.mockReturnValue({ user: { role: 'student' } });

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/student" element={<div>Student Landing</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Student Landing')).toBeInTheDocument();
  });

  it('redirects instructor user to instructor dashboard', async () => {
    mockUseAuth.mockReturnValue({ user: { role: 'instructor' } });

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/instructor" element={<div>Instructor Landing</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Instructor Landing')).toBeInTheDocument();
  });

  it('redirects admin user to head dashboard', async () => {
    mockUseAuth.mockReturnValue({ user: { role: 'admin' } });

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/head" element={<div>Head Landing</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Head Landing')).toBeInTheDocument();
  });
});
