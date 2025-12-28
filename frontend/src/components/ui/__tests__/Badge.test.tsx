import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from '../Badge'

describe('Badge Component', () => {
  it('renders children correctly', () => {
    render(<Badge>New</Badge>)
    expect(screen.getByText('New')).toBeInTheDocument()
  })

  it('applies primary variant by default', () => {
    const { container } = render(<Badge>Primary</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('bg-primary-100')
    expect(badge.className).toContain('text-primary-800')
  })

  it('applies secondary variant', () => {
    const { container } = render(<Badge variant="secondary">Secondary</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('bg-secondary-100')
  })

  it('applies success variant', () => {
    const { container } = render(<Badge variant="success">Success</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('bg-success-100')
  })

  it('applies warning variant', () => {
    const { container } = render(<Badge variant="warning">Warning</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('bg-warning-100')
  })

  it('applies danger variant', () => {
    const { container } = render(<Badge variant="danger">Danger</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('bg-danger-100')
  })

  it('applies info variant', () => {
    const { container } = render(<Badge variant="info">Info</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('bg-blue-100')
  })

  it('applies small size by default', () => {
    const { container } = render(<Badge>Small</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('text-xs')
  })

  it('applies medium size', () => {
    const { container } = render(<Badge size="md">Medium</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('text-sm')
  })

  it('applies rounded by default', () => {
    const { container } = render(<Badge>Rounded</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('rounded-full')
  })

  it('applies non-rounded when rounded is false', () => {
    const { container } = render(<Badge rounded={false}>Not Rounded</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).not.toContain('rounded-full')
    expect(badge.className).toContain('rounded')
  })

  it('applies custom className', () => {
    const { container } = render(<Badge className="custom-class">Custom</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('custom-class')
  })

  it('renders as inline element', () => {
    const { container } = render(<Badge>Inline</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('inline-flex')
  })
})
