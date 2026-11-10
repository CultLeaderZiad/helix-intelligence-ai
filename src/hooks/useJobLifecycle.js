import { useCallback, useEffect, useMemo, useRef } from "react"
import { JOB_POLL_TIMEOUT_MS } from "@/services/config"

/** One generation owns all async work and timers, independent of backend IDs. */
export function useJobLifecycle() {
  const state = useRef({ mounted: true, generation: 0, controller: null, poll: null, deadline: null })
  const clearTimers = useCallback(() => {
    clearTimeout(state.current.poll)
    clearTimeout(state.current.deadline)
    state.current.poll = null
    state.current.deadline = null
  }, [])
  const invalidate = useCallback(() => {
    // Fence callbacks before abort dispatches synchronous event listeners.
    state.current.generation += 1
    clearTimers()
    state.current.controller?.abort()
    state.current.controller = null
  }, [clearTimers])
  useEffect(() => {
    state.current.mounted = true
    return () => {
      state.current.mounted = false
      invalidate()
    }
  }, [invalidate])
  const isCurrent = useCallback((run) => Boolean(
    run && state.current.mounted && state.current.generation === run.generation && !run.signal.aborted
  ), [])
  const begin = useCallback((onTimeout) => {
    invalidate()
    if (!state.current.mounted) return null
    const controller = new AbortController()
    state.current.controller = controller
    const run = { generation: state.current.generation, signal: controller.signal }
    state.current.deadline = setTimeout(() => {
      if (!isCurrent(run)) return
      invalidate()
      onTimeout()
    }, JOB_POLL_TIMEOUT_MS)
    return run
  }, [invalidate, isCurrent])
  const schedule = useCallback((run, callback, delay) => {
    if (!isCurrent(run)) return
    clearTimeout(state.current.poll)
    state.current.poll = setTimeout(() => {
      state.current.poll = null
      if (isCurrent(run)) callback()
    }, delay)
  }, [isCurrent])
  const finish = useCallback((run) => {
    if (isCurrent(run)) clearTimers()
  }, [clearTimers, isCurrent])
  return useMemo(() => ({ begin, invalidate, isCurrent, schedule, finish }), [begin, invalidate, isCurrent, schedule, finish])
}

export function pollDelay(attempt, initial) {
  return Math.min(10000, initial * 1.5 ** Math.min(attempt, 20))
}
