import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Card } from '../Card'

describe('Card Component', () => {
  it('renders children correctly', () => {
    render(
      <Card>
        <div>Card Content</div>
      </Card>
    )
    expect(screen.getByText('Card Content')).toBeInTheDocument()
  })

  it('applies default variant classes', () => {
    const { container } = render(
      <Card>
        <div>Content</div>
      </Card>
    )
    const card = container.firstChild as HTMLElement
    expect(card.className).toContain('bg-white')
    expect(card.className).toContain('shadow-card')
    expect(card.className).toContain('rounded-xl')
  })

  it('applies custom className', () => {
    const { container } = render(
      <Card className="custom-class">
        <div>Content</div>
      </Card>
    )
    const card = container.firstChild as HTMLElement
    expect(card.className).toContain('custom-class')
  })

  it('applies hover variant', () => {
    const { container } = render(
      <Card variant="hover">
        <div>Content</div>
      </Card>
    )
    const card = container.firstChild as HTMLElement
    expect(card.className).toContain('transition-all')
    expect(card.className).toContain('hover:shadow-card-hover')
  })

  it('applies glass variant', () => {
    const { container } = render(
      <Card variant="glass">
        <div>Content</div>
      </Card>
    )
    const card = container.firstChild as HTMLElement
    expect(card.className).toContain('bg-white/70')
    expect(card.className).toContain('backdrop-blur-lg')
  })

  it('applies flat variant', () => {
    const { container } = render(
      <Card variant="flat">
        <div>Content</div>
      </Card>
    )
    const card = container.firstChild as HTMLElement
    expect(card.className).toContain('bg-white')
    expect(card.className).toContain('border')
  })

  it('applies different padding sizes', () => {
    const { container: smContainer } = render(
      <Card padding="sm">
        <div>Content</div>
      </Card>
    )
    const smCard = smContainer.firstChild as HTMLElement
    expect(smCard.className).toContain('p-4')

    const { container: lgContainer } = render(
      <Card padding="lg">
        <div>Content</div>
      </Card>
    )
    const lgCard = lgContainer.firstChild as HTMLElement
    expect(lgCard.className).toContain('p-8')
  })

  it('applies no padding when padding is none', () => {
    const { container } = render(
      <Card padding="none">
        <div>Content</div>
      </Card>
    )
    const card = container.firstChild as HTMLElement
    expect(card.className).not.toContain('p-')
  })

  it('passes through additional props', () => {
    const { container } = render(
      <Card data-testid="test-card" onClick={() => {/* noop */}}>
        <div>Content</div>
      </Card>
    )
    const card = container.firstChild as HTMLElement
    expect(card.getAttribute('data-testid')).toBe('test-card')
  })
})
