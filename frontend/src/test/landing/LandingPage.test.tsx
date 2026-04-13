import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import LandingPage from '../../features/landing/pages/LandingPage'

vi.mock('../../features/auth/hooks/useAuth', () => ({
  useAuth: () => ({ isAuthenticated: false, user: null, isLoading: false }),
}))

const renderLanding = () =>
  render(
    <BrowserRouter>
      <LandingPage />
    </BrowserRouter>
  )

describe('LandingPage', () => {
  it('renders the navbar with Sign In link', () => {
    renderLanding()
    expect(screen.getByText('Sign In')).toBeInTheDocument()
  })

  it('renders the hero headline', () => {
    renderLanding()
    expect(screen.getByText(/Drive Continuous Improvement/)).toBeInTheDocument()
  })

  it('renders the features section', () => {
    renderLanding()
    expect(screen.getByText('Outcome Tracking')).toBeInTheDocument()
    expect(screen.getByText('Data-Driven Insights')).toBeInTheDocument()
  })

  it('renders the roles section', () => {
    renderLanding()
    expect(screen.getByText('Students')).toBeInTheDocument()
    expect(screen.getByText('Instructors')).toBeInTheDocument()
    expect(screen.getByText('Department Heads')).toBeInTheDocument()
  })

  it('renders the CTA section', () => {
    renderLanding()
    expect(screen.getByText(/Ready to improve/)).toBeInTheDocument()
  })
})
