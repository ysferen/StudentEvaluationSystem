import React, { useEffect } from 'react'
import { useJobStream } from '@/shared/hooks/useJobStream'

interface JobProgressBarProps {
  jobId: number | null
  onComplete?: () => void
  label?: string
}

export const JobProgressBar: React.FC<JobProgressBarProps> = ({
  jobId,
  onComplete,
  label = 'Processing...',
}) => {
  const { progress, isComplete, error, reconnect } = useJobStream(jobId)

  useEffect(() => {
    if (isComplete && onComplete) {
      onComplete()
    }
  }, [isComplete, onComplete])

  if (!jobId || !progress) {
    return null
  }

  if (progress.status === 'failed') {
    return (
      <div className="bg-danger-50 border border-danger-200 rounded-xl p-4">
        <p className="text-danger-800 font-medium mb-2">Job failed</p>
        {progress.error && (
          <p className="text-danger-600 text-sm">{progress.error}</p>
        )}
        <button
          onClick={reconnect}
          className="mt-2 px-3 py-1 bg-danger-600 text-white text-sm rounded-lg"
        >
          Retry
        </button>
      </div>
    )
  }

  if (progress.type === 'complete') {
    return (
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
        <p className="text-emerald-800 font-medium">
          Complete: {progress.courses_created ?? progress.created ?? 0} items processed
        </p>
      </div>
    )
  }

  const pct = progress.total && progress.total > 0
    ? Math.round(((progress.current ?? 0) / progress.total) * 100)
    : 0

  return (
    <div className="bg-primary-50 border border-primary-200 rounded-xl p-4">
      <p className="text-sm text-primary-700 mb-2">
        {label} {progress.current}/{progress.total}
      </p>
      <div className="w-full bg-primary-200 rounded-full h-2">
        <div
          className="bg-primary-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      {error && (
        <p className="text-warning-600 text-xs mt-1">{error}</p>
      )}
    </div>
  )
}
