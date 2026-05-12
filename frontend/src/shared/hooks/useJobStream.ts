import { useEffect, useState, useCallback } from 'react'
import { baseURL } from '@/shared/api/mutator'
import type { JobProgressEvent } from '@/shared/api/model/jobProgressEvent'

interface UseJobStreamResult {
  progress: JobProgressEvent | null
  isComplete: boolean
  error: string | null
  reconnect: () => void
}

export function useJobStream(jobId: number | null): UseJobStreamResult {
  const [progress, setProgress] = useState<JobProgressEvent | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const [streamError, setStreamError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)

  const connect = useCallback(() => {
    if (!jobId) return () => {}

    const url = `${baseURL}/core/events/?channels=jobs.${jobId}`
    const eventSource = new EventSource(url, { withCredentials: true })

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as JobProgressEvent
        setProgress(data)
        if (data.type === 'complete') {
          setIsComplete(true)
          eventSource.close()
        }
      } catch {
        // Heartbeat messages (lines starting with ":") are not valid JSON — ignore
      }
    }

    eventSource.onerror = () => {
      setStreamError('Connection lost. Retrying...')
      // EventSource auto-reconnects by default
    }

    return () => {
      eventSource.close()
    }
  }, [jobId, retryCount])

  useEffect(() => {
    const cleanup = connect()
    return cleanup
  }, [connect])

  const reconnect = useCallback(() => {
    setIsComplete(false)
    setStreamError(null)
    setRetryCount((prev) => prev + 1)
  }, [])

  return { progress, isComplete, error: streamError, reconnect }
}
