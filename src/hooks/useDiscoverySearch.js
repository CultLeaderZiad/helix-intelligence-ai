import { useCallback, useRef, useState } from "react"
import { discoverService } from "@/services"
import { JOB_POLL_INTERVAL_MS } from "@/services/config"
import { pollDelay, useJobLifecycle } from "./useJobLifecycle"

export const PHASE = {
  IDLE: "idle",
  SUBMITTING: "submitting",
  RUNNING: "running",
  FETCHING_RESULTS: "fetching_results",
  READY: "ready",
  ERROR: "error",
  TIMED_OUT: "timed_out",
}

export function isServiceRestart(error) {
  return error?.kind === "service_restart"
}

const PAGE_SIZE = 20

/** The hook owns submission, sequential polling and result/refinement state. */
export function useDiscoverySearch() {
  const [phase, setPhase] = useState(PHASE.IDLE)
  const [job, setJob] = useState(null)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [lastParams, setLastParams] = useState(null)
  const activeJobId = useRef(null)
  const lifecycle = useJobLifecycle()

  const fetchResults = useCallback(async (run, jobId, { page = 1, sort } = {}) => {
    if (!lifecycle.isCurrent(run)) return
    setPhase(PHASE.FETCHING_RESULTS)
    try {
      const payload = await discoverService.getJobResults(jobId, {
        page, page_size: PAGE_SIZE, sort,
      }, { signal: run.signal })
      if (!lifecycle.isCurrent(run)) return
      setResults(payload)
      setPhase(PHASE.READY)
    } catch (err) {
      if (!lifecycle.isCurrent(run)) return
      setError(err)
      setPhase(PHASE.ERROR)
    } finally {
      lifecycle.finish(run)
    }
  }, [lifecycle])

  const submit = useCallback(async (params = {}) => {
    const run = lifecycle.begin(() => setPhase(PHASE.TIMED_OUT))
    activeJobId.current = null
    if (!run) return
    setError(null)
    setResults(null)
    setJob(null)
    setPhase(PHASE.SUBMITTING)
    setLastParams(params)
    try {
      const created = await discoverService.search(params, { signal: run.signal })
      if (!lifecycle.isCurrent(run)) return
      const jobId = created.job_id
      activeJobId.current = jobId
      setJob(created)
      setPhase(PHASE.RUNNING)
      let attempt = 0
      const poll = async () => {
        if (!lifecycle.isCurrent(run)) return
        try {
          const next = await discoverService.getJobStatus(jobId, { signal: run.signal })
          if (!lifecycle.isCurrent(run)) return
          setJob(next)
          if (next.status === "succeeded") {
            void fetchResults(run, jobId, { page: 1, sort: params.sort })
          } else if (next.status === "failed") {
            const failure = new Error(next.error ?? "Discovery job failed")
            failure.kind = next.failure_kind ?? "error"
            setError(failure)
            setPhase(PHASE.ERROR)
            lifecycle.finish(run)
          } else {
            lifecycle.schedule(run, poll, pollDelay(++attempt, JOB_POLL_INTERVAL_MS))
          }
        } catch (err) {
          if (!lifecycle.isCurrent(run)) return
          setError(err)
          setPhase(PHASE.ERROR)
          lifecycle.finish(run)
        }
      }
      lifecycle.schedule(run, poll, JOB_POLL_INTERVAL_MS)
    } catch (err) {
      if (!lifecycle.isCurrent(run)) return
      setError(err)
      setPhase(PHASE.ERROR)
      lifecycle.finish(run)
    }
  }, [lifecycle, fetchResults])

  const refine = useCallback(({ page, sort }) => {
    const jobId = activeJobId.current
    if (!jobId) return
    // Each refinement is a new generation, even when the job ID is unchanged.
    const run = lifecycle.begin(() => setPhase(PHASE.TIMED_OUT))
    if (!run) return
    const nextParams = { ...(lastParams ?? {}), sort: sort ?? lastParams?.sort }
    setLastParams(nextParams)
    setError(null)
    void fetchResults(run, jobId, { page, sort: nextParams.sort })
  }, [fetchResults, lastParams, lifecycle])

  const cancel = useCallback(() => {
    lifecycle.invalidate()
    activeJobId.current = null
    setPhase(PHASE.IDLE)
    setJob(null)
    setResults(null)
    setError(null)
  }, [lifecycle])

  const retry = useCallback(() => {
    if (lastParams) void submit(lastParams)
  }, [lastParams, submit])

  return {
    phase, job, results, error, lastParams, submit, refine, cancel, retry,
    isBusy: phase === PHASE.SUBMITTING || phase === PHASE.RUNNING || phase === PHASE.FETCHING_RESULTS,
    timedOut: phase === PHASE.TIMED_OUT,
  }
}
