import { useCallback, useEffect, useRef, useState } from "react"
import { mediaService, ServiceError } from "@/services"

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

  const activeJobIdRef = useRef(null)
  const pollTimerRef = useRef(null)

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return stopPolling
  }, [stopPolling])

  const checkJobStatus = useCallback(
    async (jobId) => {
      if (activeJobIdRef.current !== jobId) return

      try {
        const currentJob = await mediaService.getJob(jobId)
        if (activeJobIdRef.current !== jobId) return

        setJob(currentJob)

        if (currentJob.status === "succeeded" || currentJob.status === "completed") {
          setPhase(PHASE.FETCHING_RESULTS)
          try {
            const finalResult = await mediaService.getJobResult(jobId)
            if (activeJobIdRef.current !== jobId) return
            setResult(finalResult)
          } catch (e) {
            if (currentJob.result_url) {
              setResult({
                type: "image",
                url: currentJob.result_url,
                images: [{ url: currentJob.result_url }]
              })
            }
          }
          setPhase(PHASE.READY)
          stopPolling()
        } else if (currentJob.status === "failed") {
          const errStr = currentJob.error_message || "Generation failed"
          setError(errStr)
          setPhase(PHASE.ERROR)
          stopPolling()
        } else if (currentJob.status === "canceled") {
          setError("Generation canceled")
          setPhase(PHASE.ERROR)
          stopPolling()
        } else if (currentJob.status === "nsfw") {
          setError(currentJob.error_message || "Prompt flagged as NSFW. Generation aborted.")
          setPhase(PHASE.ERROR)
          stopPolling()
        } else {
          // Still running/queued, poll again
          pollTimerRef.current = setTimeout(() => checkJobStatus(jobId), 2000)
        }
      } catch (err) {
        if (activeJobIdRef.current !== jobId) return
        const msg = err?.message || (typeof err === "string" ? err : "Failed to check generation status")
        setError(msg)
        setPhase(PHASE.ERROR)
        stopPolling()
      }
    },
    [stopPolling],
  )

  const submit = useCallback(
    async (params) => {
      stopPolling()
      setPhase(PHASE.SUBMITTING)
      setError(null)
      setResult(null)

      try {
        const newJob = await mediaService.generate(params)
        const jobId = newJob.job_id || newJob.id
        setJob(newJob)
        activeJobIdRef.current = jobId
        setPhase(PHASE.RUNNING)
        checkJobStatus(jobId)
      } catch (err) {
        const msg = err?.message || (typeof err === "string" ? err : "Generation request failed")
        setError(msg)
        setPhase(PHASE.ERROR)
        activeJobIdRef.current = null
      }
    },
    [checkJobStatus, stopPolling],
  )

  const cancel = useCallback(async () => {
    const currentId = activeJobIdRef.current
    stopPolling()
    activeJobIdRef.current = null
    
    if (currentId) {
      try {
        await mediaService.cancel(currentId)
      } catch (err) {
        // ignore cancellation errors in UI
      }
    }
    
    setPhase(PHASE.IDLE)
    setJob(null)
    setResult(null)
    setError(null)
  }, [stopPolling])

  return {
    phase,
    job,
    result,
    error,
    submit,
    cancel,
    isBusy: phase === PHASE.SUBMITTING || phase === PHASE.RUNNING || phase === PHASE.FETCHING_RESULTS,
  }
}
