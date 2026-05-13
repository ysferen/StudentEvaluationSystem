import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

import { RecomputeJobsProvider, useRecomputeJobs } from '@/shared/contexts/RecomputeJobsContext'

const { recomputeRetrieveMock } = vi.hoisted(() => ({
  recomputeRetrieveMock: vi.fn(),
}))

const { invalidateQueriesMock } = vi.hoisted(() => ({
  invalidateQueriesMock: vi.fn(async () => ({})),
}))

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({
    invalidateQueries: invalidateQueriesMock,
  }),
}))

vi.mock('@/shared/api/generated/v1/v1', () => ({
  v1EvaluationScoreRecomputeJobsRetrieve: recomputeRetrieveMock,
}))

let eventSourceInstances: any[]

const Trigger: React.FC = () => {
  const { enqueueJobs, showAlert } = useRecomputeJobs()
  return (
    <div>
      <button
        type="button"
        onClick={() =>
          enqueueJobs([
            { id: 501, status: 'pending', task_type: 'course_recompute' },
          ])
        }
      >
        Add Job
      </button>
      <button
        type="button"
        onClick={() => showAlert('success', 'Student grades uploaded successfully.')}
      >
        Show Upload Alert
      </button>
    </div>
  )
}

describe('RecomputeJobsProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    eventSourceInstances = []
    const mockEventSource = vi.fn().mockImplementation(function (url: string, config?: any) {
      const instance = {
        url,
        config,
        onmessage: null as any,
        onerror: null as any,
        close: vi.fn(),
      }
      eventSourceInstances.push(instance)
      return instance
    })
    vi.stubGlobal('EventSource', mockEventSource)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows upload success alert and independent job alert that transitions to success', async () => {
    const user = userEvent.setup()

    render(
      <RecomputeJobsProvider>
        <Trigger />
      </RecomputeJobsProvider>
    )

    await user.click(screen.getByRole('button', { name: /add job/i }))

    expect(screen.getByText(/student grades uploaded successfully/i)).toBeInTheDocument()
    expect(screen.getByText(/score recomputation is running in the background/i)).toBeInTheDocument()
    expect(screen.getByTestId('global-upload-alert')).toHaveClass('transition-all')
    expect(screen.getByTestId('global-job-alert')).toHaveClass('transition-all')
    expect(screen.getAllByTestId('global-job-alert')).toHaveLength(1)

    // Simulate SSE "complete" event arriving
    await waitFor(() => {
      expect(eventSourceInstances.length).toBeGreaterThan(0)
    })
    const es = eventSourceInstances[0]
    es.onmessage({
      data: JSON.stringify({ type: 'complete', job_id: 501, status: 'success' }),
    })

    await waitFor(() => {
      expect(screen.getByText(/score recomputation completed successfully/i)).toBeInTheDocument()
    })

    expect(invalidateQueriesMock).toHaveBeenCalled()

    expect(screen.getAllByTestId('global-job-alert')).toHaveLength(1)
  })

  it('shows upload success alert globally even without jobs', async () => {
    const user = userEvent.setup()

    render(
      <RecomputeJobsProvider>
        <Trigger />
      </RecomputeJobsProvider>
    )

    await user.click(screen.getByRole('button', { name: /show upload alert/i }))
    expect(screen.getByText(/student grades uploaded successfully/i)).toBeInTheDocument()
    expect(screen.getByTestId('global-upload-alert')).toBeInTheDocument()
  })
})
