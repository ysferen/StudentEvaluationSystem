import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import LiveStatsSection from '../../features/landing/components/LiveStatsSection'

vi.mock('../../features/landing/hooks/useLandingStats', () => ({
  useLandingStats: () => ({
    data: { universities: 2, departments: 8, programs: 15, courses: 104 },
    isLoading: false,
  }),
}))

describe('LiveStatsSection', () => {
  it('renders all stat labels', () => {
    render(<LiveStatsSection />)
    expect(screen.getByText('Universities')).toBeInTheDocument()
    expect(screen.getByText('Departments')).toBeInTheDocument()
    expect(screen.getByText('Programs')).toBeInTheDocument()
    expect(screen.getByText('Courses')).toBeInTheDocument()
  })

  it('displays 100+ for courses over threshold', () => {
    render(<LiveStatsSection />)
    expect(screen.getByText('100+')).toBeInTheDocument()
  })
})
