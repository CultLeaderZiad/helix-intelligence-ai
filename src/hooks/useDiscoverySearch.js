import { useCallback, useEffect, useRef, useState } from "react"
import { discoverService } from "@/services"
import { JOB_POLL_INTERVAL_MS } from "@/services/config"

/**
 * ============================================================
 * DISCOVERY JOB LIFECYCLE
 * ============================================================
 * Owns the full async flow as real application state:
 *
 *   submit() -> POST job -> poll status -> succeeded -> GET results
 *
 * The progress the UI renders is the `progress` value returned by the
 * service, not a CSS keyframe. If polling stops, the bar stops. If the
 * job fails mid-flight, the UI shows the stage it died on.
 *
 * This is the only hook Discover components use to reach data; none of
 * them import a service directly.
 * ============================================================
 */

const PHASE = {
  IDLE: "idle",
  SUBMITTING: "submitting",
  RUNNING: "running",
  FETCHING_RESULTS: "fetching_results",
  READY: "ready",
  ERROR: "error",
}

export { PHASE }

const PAGE_SIZE = 20

export function useDiscoverySearch() {
  const [phase, setPhase] = useState(PHASE.IDLE)
  const [job, setJob] = useState(null)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [lastParams, setLastParams] = useState(null)

  const pollRef = useRef(null)
  const mounted = useRef(true)
  const activeJobId = useRef(null)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const fetchResults = useCallback(
    async (jobId, { page = 1, sort } = {}) => {
      setPhase(PHASE.FETCHING_RESULTS)
      try {
        const payload = await discoverService.getJobResults(jobId, {
          page,
          page_size: PAGE_SIZE,
          sort,
        })
        if (!mounted.current || activeJobId.current !== jobId) return
        setResults(payload)
        setPhase(PHASE.READY)
      } catch (err) {
        if (!mounted.current || activeJobId.current !== jobId) return
        setError(err)
        setPhase(PHASE.ERROR)
      }
    },
    [],
  )

  const submit = useCallback(
    async (params = {}) => {
      stopPolling()
      setError(null)
      setResults(null)
      setJob(null)
      setPhase(PHASE.SUBMITTING)
      setLastParams(params)

      let created
      try {
        created = await discoverService.search(params)
      } catch (err) {
        if (!mounted.current) return
        setError(err)
        setPhase(PHASE.ERROR)
        return
      }

      if (!mounted.current) return

      activeJobId.current = created.job_id
      setJob(created)
      setPhase(PHASE.RUNNING)

      // Poll. Every value the progress UI shows originates here.
      pollRef.current = setInterval(async () => {
        const jobId = activeJobId.current
        if (!jobId) return
        try {
          const next = await discoverService.getJobStatus(jobId)
          if (!mounted.current || activeJobId.current !== jobId) return
          setJob(next)

          if (next.status === "succeeded") {
            stopPolling()
            fetchResults(jobId, { page: 1, sort: params.sort })
          } else if (next.status === "failed") {
            stopPolling()
            setError(new Error(next.error ?? "Discovery job failed"))
            setPhase(PHASE.ERROR)
          }
        } catch (err) {
          if (!mounted.current) return
          stopPolling()
          setError(err)
          setPhase(PHASE.ERROR)
        }
      }, JOB_POLL_INTERVAL_MS)
    },
    [stopPolling, fetchResults],
  )

  /** Re-sort or paginate a completed set without re-running the scrape. */
  const refine = useCallback(
    ({ page, sort }) => {
      if (!activeJobId.current) return
      const nextParams = { ...(lastParams ?? {}), sort: sort ?? lastParams?.sort }
      setLastParams(nextParams)
      fetchResults(activeJobId.current, { page, sort: nextParams.sort })
    },
    [fetchResults, lastParams],
  )

  const cancel = useCallback(() => {
    stopPolling()
    activeJobId.current = null
    setPhase(PHASE.IDLE)
    setJob(null)
    setResults(null)
    setError(null)
  }, [stopPolling])

  const retry = useCallback(() => {
    if (lastParams) submit(lastParams)
  }, [lastParams, submit])

  return {
    phase,
    job,
    results,
    error,
    lastParams,
    submit,
    refine,
    cancel,
    retry,
    isBusy:
      phase === PHASE.SUBMITTING ||
      phase === PHASE.RUNNING ||
      phase === PHASE.FETCHING_RESULTS,
  }
}
