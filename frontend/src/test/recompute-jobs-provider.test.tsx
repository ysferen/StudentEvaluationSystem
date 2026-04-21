import { describe, it, expect, vi, beforeEach } from 'vitest'
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
  })

  it('shows upload success alert and independent job alert that transitions to success', async () => {
    recomputeRetrieveMock
      .mockResolvedValueOnce({ id: 501, status: 'running' })
      .mockResolvedValueOnce({ id: 501, status: 'running' })
      .mockResolvedValueOnce({ id: 501, status: 'success' })

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

    await waitFor(() => {
      expect(recomputeRetrieveMock).toHaveBeenCalledWith(501)
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
