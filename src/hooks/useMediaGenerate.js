import { useCallback, useRef, useState } from "react"
import { mediaService } from "@/services"
import { pollDelay, useJobLifecycle } from "./useJobLifecycle"

export const PHASE = {
  IDLE: "idle",
  SUBMITTING: "submitting",
  RUNNING: "running",
  FETCHING_RESULTS: "fetching_results",
  READY: "ready",
  ERROR: "error",
}

export function useMediaGenerate() {
  const [phase, setPhase] = useState(PHASE.IDLE)
  const [job, setJob] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [failureKind, setFailureKind] = useState(null)
  const activeJobId = useRef(null)
  const lifecycle = useJobLifecycle()

  const submit = useCallback(async (params) => {
    const run = lifecycle.begin(() => {
      activeJobId.current = null
      setError("Failed to check generation status")
      setFailureKind("timeout")
      setPhase(PHASE.ERROR)
    })
    activeJobId.current = null
    if (!run) return
    setPhase(PHASE.SUBMITTING)
    setJob(null)
    setError(null)
    setFailureKind(null)
    setResult(null)
    const options = { signal: run.signal }
    const fail = (err, fallback) => {
      if (!lifecycle.isCurrent(run)) return
      setError(err?.message || (typeof err === "string" ? err : fallback))
      setPhase(PHASE.ERROR)
      lifecycle.finish(run)
    }
    try {
      // Adapters may ignore options; generation fencing still protects state.
      const created = await mediaService.generate(params, options)
      if (!lifecycle.isCurrent(run)) return
      const jobId = created.job_id || created.id
      activeJobId.current = jobId
      setJob(created)
      setPhase(PHASE.RUNNING)
      let attempt = 0
      const poll = async () => {
        if (!lifecycle.isCurrent(run)) return
        try {
          const next = await mediaService.getJob(jobId, options)
          if (!lifecycle.isCurrent(run)) return
          setJob(next)
          if (next.status === "succeeded" || next.status === "completed") {
            setPhase(PHASE.FETCHING_RESULTS)
            try {
              const payload = await mediaService.getJobResult(jobId, options)
              if (!lifecycle.isCurrent(run)) return
              setResult(payload)
            } catch (err) {
              if (!lifecycle.isCurrent(run)) return
              if (!next.result_url) throw err
              setResult({ type: "image", url: next.result_url, images: [{ url: next.result_url }] })
            }
            if (!lifecycle.isCurrent(run)) return
            setPhase(PHASE.READY)
            lifecycle.finish(run)
          } else if (["failed", "canceled", "nsfw"].includes(next.status)) {
            const fallback = next.status === "canceled" ? "Generation canceled"
              : next.status === "nsfw" ? "Prompt flagged as NSFW. Generation aborted." : "Generation failed"
            setFailureKind(next.failure_kind || "error")
            fail(next.error_message, fallback)
          } else {
            lifecycle.schedule(run, poll, pollDelay(attempt++, 2000))
          }
        } catch (err) {
          fail(err, "Failed to check generation status")
        }
      }
      void poll()
    } catch (err) {
      if (!lifecycle.isCurrent(run)) return
      activeJobId.current = null
      fail(err, "Generation request failed")
    }
  }, [lifecycle])

  const cancel = useCallback(async () => {
    const jobId = activeJobId.current
    lifecycle.invalidate()
    activeJobId.current = null
    // Reset before awaiting server cancellation; its completion owns no UI state.
    setPhase(PHASE.IDLE)
    setJob(null)
    setResult(null)
    setError(null)
    setFailureKind(null)
    if (jobId) {
      try { await mediaService.cancel(jobId) } catch { /* best effort */ }
    }
  }, [lifecycle])

  return {
    phase, job, result, error, failureKind,
    isServiceRestart: failureKind === "service_restart",
    submit, cancel,
    isBusy: phase === PHASE.SUBMITTING || phase === PHASE.RUNNING || phase === PHASE.FETCHING_RESULTS,
  }
}
