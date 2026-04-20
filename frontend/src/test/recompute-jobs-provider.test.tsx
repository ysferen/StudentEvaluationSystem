import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

import { RecomputeJobsProvider, useRecomputeJobs } from '@/shared/contexts/RecomputeJobsContext'

const { recomputeRetrieveMock } = vi.hoisted(() => ({
  recomputeRetrieveMock: vi.fn(),
}))

vi.mock('@/shared/api/generated/v1/v1', () => ({
  v1EvaluationScoreRecomputeJobsRetrieve: recomputeRetrieveMock,
}))

const Trigger: React.FC = () => {
  const { enqueueJobs } = useRecomputeJobs()
  return (
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
  )
}

describe('RecomputeJobsProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('polls queued jobs and shows global progress/completion notifications', async () => {
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

    expect(screen.getByText(/background score recomputation in progress/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(recomputeRetrieveMock).toHaveBeenCalledWith(501)
    })

    await waitFor(() => {
      expect(screen.getByText(/score recomputation completed successfully/i)).toBeInTheDocument()
    })
  })
})
