import { useCallback, useEffect, useRef, useState } from "react"
import { discoverService } from "@/services"
import { getAccessToken } from "@/services/sessionStore"
import { JOB_POLL_INTERVAL_MS } from "@/services/config"
import { pollDelay, useJobLifecycle } from "./useJobLifecycle"

export const PHASE = {
  IDLE: "idle",
  SUBMITTING: "submitting",
  RUNNING: "running",
  FETCHING_RESULTS: "fetching_results",
  READY: "ready",
  ERROR: "error",
  CANCELLING: "cancelling",
  CANCEL_ERROR: "cancel_error",
  CANCELLED: "cancelled",
  TIMED_OUT: "timed_out",
}

export function isServiceRestart(error) {
  return error?.kind === "service_restart"
}

const PAGE_SIZE = 20
const TERMINAL_STATUSES = new Set([
  "succeeded", "failed", "cancelled", "canceled", "timed_out",
])
const CANCELLING_STATUSES = new Set(["cancelling", "cancel_requested"])

function isTerminalStatus(status) {
  return TERMINAL_STATUSES.has(status)
}

function isDocumentVisible() {
  return typeof document === "undefined" || document.visibilityState !== "hidden"
}

function jobFromResponse(response) {
  if (!response || typeof response !== "object") return null
  const job = response.job && typeof response.job === "object" ? response.job : response
  return typeof job.status === "string" ? job : null
}

/** The hook owns submission, sequential polling and result/refinement state. */
export function useDiscoverySearch() {
  const [phase, setPhase] = useState(PHASE.IDLE)
  const [job, setJob] = useState(null)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [cancelError, setCancelError] = useState(null)
  const [lastParams, setLastParams] = useState(null)
  const activeJobId = useRef(null)
  const activeJobRef = useRef(null)
  const operationRef = useRef(0)
  const pollStateRef = useRef(null)
  const pollJobRef = useRef(null)
  const cancelRequestsRef = useRef(new Map())
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

  function isCurrentContext(context) {
    const active = activeJobRef.current
    return Boolean(
      context && active &&
      active.jobId === context.jobId &&
      active.operationId === context.operationId &&
      operationRef.current === context.operationId
    )
  }

  function callServerCancel(context) {
    const pending = cancelRequestsRef.current.get(context.jobId)
    if (pending) return pending
    if (typeof discoverService.cancelJob !== "function") {
      return Promise.reject(new Error("Server cancellation is unavailable"))
    }

    // Deliberately omit the search AbortSignal: aborting that request must not
    // abort the request that asks the worker to stop.
    const request = Promise.resolve().then(() => discoverService.cancelJob(context.jobId))
    const tracked = request.finally(() => {
      if (cancelRequestsRef.current.get(context.jobId) === tracked) {
        cancelRequestsRef.current.delete(context.jobId)
      }
    })
    cancelRequestsRef.current.set(context.jobId, tracked)
    return tracked
  }

  function finishTerminal(run, context, next, params) {
    context.status = next.status
    context.cancelRequested = false
    context.cancelFailed = false
    setJob(next)
    setCancelError(null)
    setError(null)

    if (next.status === "succeeded") {
      void fetchResults(run, context.jobId, { page: 1, sort: params.sort })
      return
    }

    lifecycle.finish(run)
    pollStateRef.current = null
    if (next.status === "failed") {
      setError(new Error(next.error ?? "Discovery job failed"))
      setPhase(PHASE.ERROR)
    } else if (next.status === "timed_out") {
      activeJobId.current = null
      setPhase(PHASE.TIMED_OUT)
    } else {
      activeJobId.current = null
      setPhase(PHASE.CANCELLED)
    }
  }

  function schedulePoll(state, delay) {
    lifecycle.schedule(state.run, () => {
      if (!isCurrentContext(state.context) || !lifecycle.isCurrent(state.run)) return
      if (!isDocumentVisible()) {
        state.waitingForVisible = true
        return
      }
      pollJobRef.current?.(state)
    }, delay)
  }

  function startPolling(run, context, params, delay = 0) {
    const state = {
      run,
      context,
      params,
      attempt: 0,
      inFlight: false,
      waitingForVisible: false,
    }
    pollStateRef.current = state
    if (delay > 0) schedulePoll(state, delay)
    else pollJobRef.current?.(state)
  }

  function startOperation(context, onTimeout) {
    const operationId = ++operationRef.current
    const nextContext = { ...context, operationId }
    activeJobRef.current = nextContext
    const run = lifecycle.begin(() => onTimeout(nextContext))
    return run ? { run, context: nextContext } : null
  }

  function markCancellationUnconfirmed(context) {
    if (!isCurrentContext(context)) return
    context.cancelFailed = true
    setCancelError(new Error("The server has not confirmed a terminal outcome."))
    setPhase(PHASE.CANCEL_ERROR)
    pollStateRef.current = null
  }

  function requestCancellation(context, reason) {
    if (!isCurrentContext(context)) return
    if (getAccessToken() !== context.sessionToken) {
      const next = startOperation(context, markCancellationUnconfirmed)
      if (!next) return
      lifecycle.finish(next.run)
      pollStateRef.current = null
      setCancelError(new Error("The session that started this search is no longer active."))
      setPhase(PHASE.CANCEL_ERROR)
      return
    }

    const operation = startOperation(
      { ...context, cancelRequested: true, cancelFailed: false, cancelReason: reason },
      markCancellationUnconfirmed,
    )
    if (!operation) return
    const { run, context: current } = operation
    pollStateRef.current = null
    setCancelError(null)
    setError(null)
    setPhase(PHASE.CANCELLING)

    void (async () => {
      try {
        const response = await callServerCancel(current)
        if (!isCurrentContext(current) || !lifecycle.isCurrent(run)) return
        const returnedJob = jobFromResponse(response)
        if (returnedJob) {
          const next = {
            ...job,
            ...returnedJob,
            job_id: returnedJob.job_id ?? current.jobId,
          }
          setJob(next)
          current.status = next.status
          if (isTerminalStatus(next.status)) {
            finishTerminal(run, current, next, current.params)
            return
          }
          if (CANCELLING_STATUSES.has(next.status)) current.cancelRequested = true
        }
        current.cancelFailed = false
        setPhase(PHASE.CANCELLING)
        startPolling(run, current, current.params)
      } catch (err) {
        if (!isCurrentContext(current) || !lifecycle.isCurrent(run)) return
        current.cancelRequested = false
        current.cancelFailed = true
        setCancelError(err)
        setPhase(PHASE.CANCEL_ERROR)
        startPolling(run, current, current.params)
      }
    })()
  }

  function onJobDeadline(operationId) {
    if (operationRef.current !== operationId) return
    const context = activeJobRef.current
    if (context?.operationId === operationId) {
      if (isTerminalStatus(context.status)) {
        setCancelError(new Error("The results request timed out."))
        setPhase(PHASE.TIMED_OUT)
      } else if (context.cancelRequested) {
        markCancellationUnconfirmed(context)
      } else {
        requestCancellation(context, "client_timeout")
      }
      return
    }

    setCancelError(new Error("The request timed out before a job ID was received."))
    setPhase(PHASE.TIMED_OUT)
  }

  function pollJob(state) {
    if (
      state.inFlight ||
      !isCurrentContext(state.context) ||
      !lifecycle.isCurrent(state.run)
    ) return
    if (!isDocumentVisible()) {
      state.waitingForVisible = true
      return
    }
    if (getAccessToken() !== state.context.sessionToken) {
      markCancellationUnconfirmed(state.context)
      lifecycle.finish(state.run)
      return
    }

    state.waitingForVisible = false
    state.inFlight = true
    void (async () => {
      try {
        const next = await discoverService.getJobStatus(state.context.jobId, {
          signal: state.run.signal,
        })
        if (!isCurrentContext(state.context) || !lifecycle.isCurrent(state.run)) return
        state.context.status = next.status
        if (CANCELLING_STATUSES.has(next.status)) state.context.cancelRequested = true
        setJob(next)
        if (isTerminalStatus(next.status)) {
          finishTerminal(state.run, state.context, next, state.params)
          return
        }

        setPhase(
          state.context.cancelFailed
            ? PHASE.CANCEL_ERROR
            : state.context.cancelRequested
              ? PHASE.CANCELLING
            : PHASE.RUNNING,
        )
        state.attempt += 1
        schedulePoll(state, pollDelay(state.attempt, JOB_POLL_INTERVAL_MS))
      } catch (err) {
        if (!isCurrentContext(state.context) || !lifecycle.isCurrent(state.run)) return
        if (state.context.cancelRequested) {
          state.context.cancelFailed = true
          setCancelError(err)
          setPhase(PHASE.CANCEL_ERROR)
        } else {
          setError(err)
          setPhase(PHASE.ERROR)
        }
        lifecycle.finish(state.run)
        pollStateRef.current = null
      } finally {
        state.inFlight = false
      }
    })()
  }
  pollJobRef.current = pollJob

  useEffect(() => {
    function onVisibilityChange() {
      if (!isDocumentVisible()) return
      const state = pollStateRef.current
      if (state?.waitingForVisible && !state.inFlight) {
        state.waitingForVisible = false
        pollJobRef.current?.(state)
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange)
    return () => document.removeEventListener("visibilitychange", onVisibilityChange)
  }, [])

  useEffect(() => () => {
    const context = activeJobRef.current
    if (
      context && !isTerminalStatus(context.status) &&
      !context.cancelRequested && getAccessToken() === context.sessionToken
    ) {
      context.cancelRequested = true
      void callServerCancel(context).catch(() => {})
    }
  }, [])

  function submit(params = {}) {
    const previous = activeJobRef.current
    if (previous && !isTerminalStatus(previous.status)) {
      requestCancellation(previous, "superseded")
      return
    }

    const operationId = ++operationRef.current
    const sessionToken = getAccessToken()
    const run = lifecycle.begin(() => onJobDeadline(operationId))
    if (!run) return
    activeJobRef.current = null
    activeJobId.current = null
    pollStateRef.current = null
    setError(null)
    setCancelError(null)
    setResults(null)
    setJob(null)
    setPhase(PHASE.SUBMITTING)
    setLastParams(params)

    void (async () => {
      try {
        const created = await discoverService.search(params, { signal: run.signal })
        if (!lifecycle.isCurrent(run)) {
          if (getAccessToken() === sessionToken && created?.job_id) {
            const staleContext = {
              jobId: created.job_id,
              sessionToken,
              operationId,
            }
            void callServerCancel(staleContext).catch(() => {})
          }
          return
        }
        const jobId = created.job_id
        const context = {
          jobId,
          sessionToken,
          operationId,
          status: created.status ?? "queued",
          params,
          cancelRequested: false,
          cancelFailed: false,
          cancelReason: null,
        }
        activeJobRef.current = context
        activeJobId.current = jobId
        setJob(created)
        setPhase(PHASE.RUNNING)
        startPolling(run, context, params, JOB_POLL_INTERVAL_MS)
      } catch (err) {
        if (!lifecycle.isCurrent(run)) return
        setError(err)
        setPhase(PHASE.ERROR)
        lifecycle.finish(run)
      }
    })()
  }

  function refine({ page, sort }) {
    const jobId = activeJobId.current
    if (!jobId) return
    const context = activeJobRef.current
    if (!context || context.status !== "succeeded") return
    const run = lifecycle.begin(() => onJobDeadline(context.operationId))
    if (!run) return
    const nextParams = { ...(lastParams ?? {}), sort: sort ?? lastParams?.sort }
    setLastParams(nextParams)
    setError(null)
    void fetchResults(run, jobId, { page, sort: nextParams.sort })
  }

  function cancel() {
    const context = activeJobRef.current
    if (context && !isTerminalStatus(context.status)) {
      requestCancellation(context, "user")
      return
    }

    if (context?.status === "succeeded" && phase === PHASE.FETCHING_RESULTS) {
      operationRef.current += 1
      lifecycle.invalidate()
      pollStateRef.current = null
      activeJobRef.current = null
      activeJobId.current = null
      setPhase(PHASE.IDLE)
      setJob(null)
      setResults(null)
      setError(null)
      setCancelError(null)
      return
    }

    if (phase === PHASE.SUBMITTING) {
      operationRef.current += 1
      lifecycle.invalidate()
      pollStateRef.current = null
      setPhase(PHASE.IDLE)
      setJob(null)
      setResults(null)
      setError(null)
      setCancelError(null)
    }
  }

  function retry() {
    const context = activeJobRef.current
    if (context && !isTerminalStatus(context.status)) {
      const operation = startOperation(context, nextContext => onJobDeadline(nextContext.operationId))
      if (!operation) return
      setError(null)
      if (operation.context.cancelFailed) {
        setPhase(PHASE.CANCEL_ERROR)
      } else if (operation.context.cancelRequested) {
        setPhase(PHASE.CANCELLING)
      } else {
        setPhase(PHASE.RUNNING)
      }
      startPolling(operation.run, operation.context, operation.context.params)
      return
    }
    if (lastParams) submit(lastParams)
  }

  const isBusy = [
    PHASE.SUBMITTING,
    PHASE.RUNNING,
    PHASE.FETCHING_RESULTS,
    PHASE.CANCELLING,
    PHASE.CANCEL_ERROR,
  ].includes(phase)

  return {
    phase,
    job,
    results,
    error,
    cancelError,
    lastParams,
    submit,
    refine,
    cancel,
    retry,
    isBusy,
    isCancelling: phase === PHASE.CANCELLING,
    timedOut: phase === PHASE.TIMED_OUT,
  }
}
