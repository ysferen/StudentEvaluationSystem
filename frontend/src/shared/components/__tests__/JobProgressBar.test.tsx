import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { JobProgressBar } from '../JobProgressBar'

const mockEventSource = {
  close: vi.fn(),
  onmessage: null as ((event: MessageEvent) => void) | null,
  onerror: null as (() => void) | null,
}

// Regular function, not arrow — EventSource must be new-able
const MockEventSource = vi.fn(function (this: any, _url: string, _config?: EventSourceInit) {
  Object.assign(mockEventSource, {
    close: vi.fn(),
    onmessage: null as ((event: MessageEvent) => void) | null,
    onerror: null as (() => void) | null,
  })
  return mockEventSource
})

vi.stubGlobal('EventSource', MockEventSource)

const fireMessage = (data: object) => {
  act(() => {
    mockEventSource.onmessage?.({
      data: JSON.stringify(data),
    } as MessageEvent)
  })
}

describe('JobProgressBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    mockEventSource.close = vi.fn()
    mockEventSource.onmessage = null
    mockEventSource.onerror = null
  })

  it('renders nothing when jobId is null', () => {
    const { container } = render(<JobProgressBar jobId={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when no progress yet', () => {
    const { container } = render(<JobProgressBar jobId={42} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders progress bar with percentage', () => {
    render(<JobProgressBar jobId={42} label="Creating courses..." />)
    fireMessage({ type: 'progress', job_id: 42, status: 'running', current: 5, total: 10 })
    expect(screen.getByText('Creating courses... 5/10')).toBeDefined()
    expect(screen.getByRole('progressbar')).toBeDefined()
  })

  it('renders complete state', () => {
    render(<JobProgressBar jobId={42} />)
    fireMessage({ type: 'complete', job_id: 42, status: 'success', courses_created: 8 })
    expect(screen.getByText('Complete: 8 items processed')).toBeDefined()
  })

  it('calls onComplete when job finishes', () => {
    const onComplete = vi.fn()
    render(<JobProgressBar jobId={42} onComplete={onComplete} />)
    fireMessage({ type: 'complete', job_id: 42, status: 'success', courses_created: 1 })
    expect(onComplete).toHaveBeenCalledTimes(1)
  })

  it('renders error state with retry button', () => {
    render(<JobProgressBar jobId={42} />)
    fireMessage({ type: 'complete', job_id: 42, status: 'failed', error: 'Template 3 failed to clone' })
    expect(screen.getByText('Job failed')).toBeDefined()
    expect(screen.getByText('Template 3 failed to clone')).toBeDefined()
  })
})
