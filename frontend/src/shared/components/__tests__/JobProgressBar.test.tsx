import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { JobProgressBar } from '../JobProgressBar'

vi.mock('@/shared/hooks/useJobStream', () => ({
  useJobStream: vi.fn(),
}))

import { useJobStream } from '@/shared/hooks/useJobStream'

describe('JobProgressBar', () => {
  beforeEach(() => {
    vi.mocked(useJobStream).mockReturnValue({
      progress: null,
      isComplete: false,
      error: null,
      reconnect: vi.fn(),
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
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
    vi.mocked(useJobStream).mockReturnValue({
      progress: {
        type: 'progress',
        job_id: 42,
        status: 'running',
        current: 5,
        total: 10,
      },
      isComplete: false,
      error: null,
      reconnect: vi.fn(),
    })

    render(<JobProgressBar jobId={42} label="Creating courses..." />)
    expect(screen.getByText('Creating courses... 5/10')).toBeDefined()
    expect(screen.getByRole('progressbar')).toBeDefined()
  })

  it('renders complete state', () => {
    vi.mocked(useJobStream).mockReturnValue({
      progress: {
        type: 'complete',
        job_id: 42,
        status: 'success',
        courses_created: 8,
      },
      isComplete: true,
      error: null,
      reconnect: vi.fn(),
    })

    render(<JobProgressBar jobId={42} />)
    expect(screen.getByText('Complete: 8 items processed')).toBeDefined()
  })

  it('calls onComplete when job finishes', () => {
    const onComplete = vi.fn()
    vi.mocked(useJobStream).mockReturnValue({
      progress: {
        type: 'complete',
        job_id: 42,
        status: 'success',
        courses_created: 1,
      },
      isComplete: true,
      error: null,
      reconnect: vi.fn(),
    })

    render(<JobProgressBar jobId={42} onComplete={onComplete} />)
    expect(onComplete).toHaveBeenCalledTimes(1)
  })

  it('renders error state with retry button', () => {
    const reconnect = vi.fn()
    vi.mocked(useJobStream).mockReturnValue({
      progress: {
        type: 'complete',
        job_id: 42,
        status: 'failed',
        error: 'Template 3 failed to clone',
      },
      isComplete: true,
      error: null,
      reconnect,
    })

    render(<JobProgressBar jobId={42} />)
    expect(screen.getByText('Job failed')).toBeDefined()
    expect(screen.getByText('Template 3 failed to clone')).toBeDefined()
  })
})
