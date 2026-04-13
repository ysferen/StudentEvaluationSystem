import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Navbar from '../../features/landing/components/Navbar'

const renderNavbar = () =>
  render(
    <BrowserRouter>
      <Navbar />
    </BrowserRouter>
  )

describe('Navbar', () => {
  it('renders the SES logo', () => {
    renderNavbar()
    expect(screen.getByText('SES')).toBeInTheDocument()
  })

  it('renders navigation links', () => {
    renderNavbar()
    expect(screen.getByText('Features')).toBeInTheDocument()
    expect(screen.getByText('How It Works')).toBeInTheDocument()
    expect(screen.getByText('Roles')).toBeInTheDocument()
  })

  it('renders sign in button', () => {
    renderNavbar()
    expect(screen.getByText('Sign In')).toBeInTheDocument()
  })
})
