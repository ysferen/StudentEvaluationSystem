import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { Outlet } from 'react-router-dom';

import App from '../App';

vi.mock('../shared/components', () => ({
  Layout: () => (
    <div>
      <Outlet />
    </div>
  ),
}));

vi.mock('../features/landing/pages/LoginPage', () => ({
  default: () => <div>Login Page</div>,
}));
vi.mock('../features/landing/pages/LandingPage', () => ({
  default: () => <div>Landing Page</div>,
}));
vi.mock('../features/dashboard/pages/Dashboard', () => ({
  default: () => <div>Root Dashboard</div>,
}));
vi.mock('../features/courses/pages/CourseDetail', () => ({
  default: () => <div>Course Detail</div>,
}));
vi.mock('../features/dashboard/pages/StudentDashboard', () => ({
  default: () => <div>Student Dashboard</div>,
}));
vi.mock('../features/courses/pages/StudentCourseDetail', () => ({
  default: () => <div>Student Course Detail</div>,
}));
vi.mock('../features/dashboard/pages/InstructorDashboard', () => ({
  default: () => <div>Instructor Dashboard</div>,
}));
vi.mock('../features/dashboard/pages/HeadDashboard', () => ({
  default: () => <div>Head Dashboard</div>,
}));
vi.mock('../features/courses/pages/StudentCourses', () => ({
  default: () => <div>Student Courses</div>,
}));
vi.mock('../features/courses/pages/InstructorCourses', () => ({
  default: () => <div>Instructor Courses</div>,
}));
vi.mock('../features/courses/pages/HeadCourses', () => ({
  default: () => <div>Head Courses</div>,
}));
vi.mock('../features/settings/pages/Settings', () => ({
  default: () => <div>Settings Page</div>,
}));
vi.mock('../features/settings/pages/Safety', () => ({
  default: () => <div>Safety Page</div>,
}));

describe('App routes', () => {
  it('renders landing page at root route', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByText('Landing Page')).toBeInTheDocument();
  });

  it('renders login route', async () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByText('Login Page')).toBeInTheDocument();
  });

  it('renders student nested route', async () => {
    render(
      <MemoryRouter initialEntries={['/student/courses']}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByText('Student Courses')).toBeInTheDocument();
  });

  it('redirects legacy lecturer route to instructor index', async () => {
    render(
      <MemoryRouter initialEntries={['/lecturer']}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByText('Instructor Dashboard')).toBeInTheDocument();
  });

  it('redirects legacy /course/:id route to landing page', async () => {
    render(
      <MemoryRouter initialEntries={['/course/10']}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByText('Landing Page')).toBeInTheDocument();
  });
});
