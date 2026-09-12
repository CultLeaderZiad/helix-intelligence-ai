import { useCallback, useEffect, useRef, useState } from "react"
import { monitorService } from "@/services"

// A monitor run is a full discovery run, so it finishes on the order of
// minutes. Polling exists only so a run that completes while the page is open
// reflects itself without a manual refresh.
const POLL_INTERVAL_MS = 20000

export function useMonitors() {
  const [monitors, setMonitors] = useState([])
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const mountedRef = useRef(true)

  const load = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true)
    try {
      const [nextMonitors, nextEvents] = await Promise.all([
        monitorService.listMonitors(),
        monitorService.listEvents({ limit: 100 }),
      ])
      if (!mountedRef.current) return
      setMonitors(Array.isArray(nextMonitors) ? nextMonitors : [])
      setEvents(Array.isArray(nextEvents) ? nextEvents : [])
      setError(null)
    } catch (err) {
      if (!mountedRef.current) return
      // A background refresh that fails must not blank out data the user is
      // already reading.
      if (!quiet) setError(err)
    } finally {
      if (mountedRef.current && !quiet) setLoading(false)
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    load()
    return () => {
      mountedRef.current = false
    }
  }, [load])

  // Only poll while something is actually in flight.
  const hasRunning = monitors.some((m) => m.last_run?.status === "running")
  useEffect(() => {
    if (!hasRunning) return undefined
    const id = setInterval(() => load({ quiet: true }), POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [hasRunning, load])

  const withAction = useCallback(
    async (fn) => {
      setActionError(null)
      try {
        await fn()
        await load({ quiet: true })
        return true
      } catch (err) {
        if (mountedRef.current) setActionError(err)
        return false
      }
    },
    [load],
  )

  return {
    monitors,
    events,
    loading,
    error,
    actionError,
    clearActionError: () => setActionError(null),
    refresh: load,
    createMonitor: (payload) => withAction(() => monitorService.createMonitor(payload)),
    updateMonitor: (id, changes) => withAction(() => monitorService.updateMonitor(id, changes)),
    deleteMonitor: (id) => withAction(() => monitorService.deleteMonitor(id)),
    runNow: (id) => withAction(() => monitorService.runNow(id)),
  }
}
