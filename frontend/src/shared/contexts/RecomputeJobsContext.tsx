import React, { createContext, useContext, useMemo, useState, useEffect } from 'react'
import { v1EvaluationScoreRecomputeJobsRetrieve } from '@/shared/api/generated/v1/v1'

type RecomputeJobStatus = 'pending' | 'running' | 'success' | 'failed'

interface RecomputeJob {
  id: number
  status: RecomputeJobStatus
  task_type?: string
}

interface NotificationState {
  type: 'success' | 'error' | 'info'
  message: string
}

interface RecomputeJobsContextValue {
  enqueueJobs: (jobs: Array<{ id?: number; status?: string; task_type?: string }>) => void
}

const RecomputeJobsContext = createContext<RecomputeJobsContextValue | undefined>(undefined)

export const useRecomputeJobs = (): RecomputeJobsContextValue => {
  const ctx = useContext(RecomputeJobsContext)
  if (!ctx) {
    throw new Error('useRecomputeJobs must be used within RecomputeJobsProvider')
  }
  return ctx
}

export const RecomputeJobsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [jobs, setJobs] = useState<RecomputeJob[]>([])
  const [notification, setNotification] = useState<NotificationState | null>(null)

  const enqueueJobs = (incomingJobs: Array<{ id?: number; status?: string; task_type?: string }>) => {
    const normalized: RecomputeJob[] = incomingJobs
      .map((job) => {
        const id = Number(job.id)
        if (Number.isNaN(id)) return null
        const status = job.status
        if (status !== 'pending' && status !== 'running' && status !== 'success' && status !== 'failed') {
          return null
        }
        return {
          id,
          status,
          task_type: job.task_type,
        }
      })
      .filter((job): job is RecomputeJob => job !== null)

    if (normalized.length === 0) {
      return
    }

    setJobs((prev) => {
      const byId = new Map(prev.map((job) => [job.id, job]))
      normalized.forEach((job) => {
        byId.set(job.id, job)
      })
      return Array.from(byId.values())
    })
  }

  useEffect(() => {
    if (jobs.length === 0) return

    const allTerminal = jobs.every((job) => job.status === 'success' || job.status === 'failed')
    if (allTerminal) {
      const hasFailed = jobs.some((job) => job.status === 'failed')
      setNotification({
        type: hasFailed ? 'error' : 'success',
        message: hasFailed
          ? 'Grade import finished, but some score recomputation jobs failed.'
          : 'Score recomputation completed successfully.',
      })
      setJobs([])
      return
    }

    let cancelled = false

    const poll = async () => {
      try {
        const pendingIds = jobs
          .filter((job) => job.status === 'pending' || job.status === 'running')
          .map((job) => job.id)

        if (pendingIds.length === 0) return

        const updates = await Promise.all(
          pendingIds.map((jobId) => v1EvaluationScoreRecomputeJobsRetrieve(jobId))
        )

        if (cancelled) return

        const updatesById = new Map(
          updates.map((update) => [Number(update.id), update.status as RecomputeJobStatus])
        )

        setJobs((prev) => {
          let changed = false
          const next = prev.map((job) => {
            const status = updatesById.get(job.id)
            if (!status || status === job.status) return job
            changed = true
            return { ...job, status }
          })
          return changed ? next : prev
        })
      } catch {
        // keep polling; next tick retries
      }
    }

    void poll()
    const interval = window.setInterval(() => {
      void poll()
    }, 1000)

    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [jobs])

  useEffect(() => {
    if (!notification) return
    const timer = window.setTimeout(() => setNotification(null), 4500)
    return () => window.clearTimeout(timer)
  }, [notification])

  const value = useMemo<RecomputeJobsContextValue>(() => ({ enqueueJobs }), [])

  return (
    <RecomputeJobsContext.Provider value={value}>
      {children}
      {jobs.length > 0 && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[70] w-full max-w-xl px-4">
          <div className="shadow-lg rounded-lg border px-4 py-3 bg-blue-50 border-blue-200 text-blue-800">
            <p className="text-sm font-medium">Background score recomputation in progress...</p>
          </div>
        </div>
      )}
      {notification && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[71] w-full max-w-xl px-4">
          <div
            className={`relative shadow-lg rounded-lg border px-4 py-3 pr-10 ${
              notification.type === 'success'
                ? 'bg-green-50 border-green-200 text-green-800'
                : notification.type === 'error'
                  ? 'bg-red-50 border-red-200 text-red-800'
                  : 'bg-blue-50 border-blue-200 text-blue-800'
            }`}
          >
            <p className="text-sm font-medium">{notification.message}</p>
            <button
              type="button"
              aria-label="Close global recompute notification"
              className="absolute top-1/2 right-7 -translate-y-1/2 text-current/70 hover:text-current"
              onClick={() => setNotification(null)}
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </RecomputeJobsContext.Provider>
  )
}
