import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import LoginPage from '../../features/landing/pages/LoginPage'

vi.mock('../../features/auth/hooks/useAuth', () => ({
  useAuth: () => ({ isAuthenticated: false, user: null, login: vi.fn(), isLoading: false }),
}))

const renderLogin = () =>
  render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>
  )

describe('LoginPage', () => {
  it('renders the welcome heading', () => {
    renderLogin()
    expect(screen.getByText('Welcome back')).toBeInTheDocument()
  })

  it('renders username and password fields', () => {
    renderLogin()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it('renders the sign in button', () => {
    renderLogin()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('renders demo accounts', () => {
    renderLogin()
    expect(screen.getByText(/demo accounts/i)).toBeInTheDocument()
  })
})
