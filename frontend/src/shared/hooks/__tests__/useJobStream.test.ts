import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useJobStream } from '../useJobStream'

/* eslint-disable @typescript-eslint/no-explicit-any */
describe('useJobStream', () => {
  let mockEventSource: any
  let eventSourceInstances: any[]

  beforeEach(() => {
    eventSourceInstances = []
    mockEventSource = vi.fn().mockImplementation(function (url: string, config?: any) {
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

  it('returns null progress when jobId is null', () => {
    const { result } = renderHook(() => useJobStream(null))
    expect(result.current.progress).toBeNull()
    expect(result.current.isComplete).toBe(false)
  })

  it('creates EventSource with correct URL when jobId is provided', () => {
    renderHook(() => useJobStream(42))

    expect(mockEventSource).toHaveBeenCalled()
    const url = mockEventSource.mock.calls[0][0] as string
    expect(url).toContain('channels=jobs.42')
    expect(url).toContain('/api/core/events/')
  })

  it('sets isComplete when complete event received', () => {
    const { result } = renderHook(() => useJobStream(42))

    act(() => {
      const instance = eventSourceInstances[0]
      instance.onmessage({
        data: JSON.stringify({
          type: 'complete',
          job_id: 42,
          status: 'success',
          courses_created: 5,
        }),
      })
    })

    expect(result.current.isComplete).toBe(true)
    expect(result.current.progress?.courses_created).toBe(5)
    expect(eventSourceInstances[0].close).toHaveBeenCalled()
  })

  it('does not set isComplete for progress events', () => {
    const { result } = renderHook(() => useJobStream(42))

    act(() => {
      const instance = eventSourceInstances[0]
      instance.onmessage({
        data: JSON.stringify({
          type: 'progress',
          job_id: 42,
          status: 'running',
          current: 3,
          total: 10,
        }),
      })
    })

    expect(result.current.isComplete).toBe(false)
    expect(result.current.progress?.current).toBe(3)
    expect(result.current.progress?.total).toBe(10)
  })

  it('ignores heartbeat messages (non-JSON)', () => {
    const { result } = renderHook(() => useJobStream(42))

    act(() => {
      const instance = eventSourceInstances[0]
      instance.onmessage({ data: ': heartbeat' })
    })

    expect(result.current.progress).toBeNull()
  })

  it('closes EventSource on unmount', () => {
    const { unmount } = renderHook(() => useJobStream(42))
    unmount()
    expect(eventSourceInstances[0].close).toHaveBeenCalled()
  })
})
