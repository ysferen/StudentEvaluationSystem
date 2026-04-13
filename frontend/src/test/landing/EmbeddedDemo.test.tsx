import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import EmbeddedDemo from '../../features/landing/components/EmbeddedDemo'

describe('EmbeddedDemo', () => {
  it('renders with assessment step visible by default', () => {
    render(<EmbeddedDemo />)
    expect(screen.getAllByText('Midterm Exam')[0]).toBeInTheDocument()
  })

  it('switches to LO view when LO step is clicked', async () => {
    const user = userEvent.setup()
    render(<EmbeddedDemo />)
    await user.click(screen.getByText('LO 3.2'))
    expect(screen.getByText('Apply statistical methods to engineering problems')).toBeInTheDocument()
  })

  it('switches to PO view when PO step is clicked', async () => {
    const user = userEvent.setup()
    render(<EmbeddedDemo />)
    await user.click(screen.getByText('PO 1'))
    expect(screen.getByText('Engineering knowledge and problem analysis')).toBeInTheDocument()
  })
})
