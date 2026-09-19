import { useState, useEffect, useRef, useCallback } from "react"
import { scoutService } from "@/services"

export const SCOUT_PHASE = {
  IDLE: "idle",
  RUNNING: "running",
  READY: "ready",
  ERROR: "error",
}

export function useScoutSearch() {
  const [phase, setPhase] = useState(SCOUT_PHASE.IDLE)
  const [job, setJob] = useState(null)
  const [leads, setLeads] = useState([])
  const [selectedLead, setSelectedLead] = useState(null)
  const [error, setError] = useState(null)
  const [isBusy, setIsBusy] = useState(false)
  const pollTimerRef = useRef(null)
  const lastParamsRef = useRef(null)

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  const pollJob = useCallback(
    (jobId) => {
      stopPolling()
      pollTimerRef.current = setInterval(async () => {
        try {
          const updatedJob = await scoutService.getJob(jobId)
          setJob(updatedJob)

          if (updatedJob.status === "succeeded") {
            stopPolling()
            const leadsData = await scoutService.getLeads(jobId)
            const items = leadsData.items || []
            setLeads(items)
            setSelectedLead(items[0] || null)
            setPhase(SCOUT_PHASE.READY)
            setIsBusy(false)
          } else if (updatedJob.status === "failed") {
            stopPolling()
            setError(updatedJob.error_msg || "Scout job encountered an error")
            setPhase(SCOUT_PHASE.ERROR)
            setIsBusy(false)
          }
        } catch (err) {
          stopPolling()
          setError(err.message || "Failed to retrieve job status")
          setPhase(SCOUT_PHASE.ERROR)
          setIsBusy(false)
        }
      }, 750)
    },
    [stopPolling]
  )

  const submit = useCallback(
    async ({ platforms, handles, enrich_emails = true }) => {
      lastParamsRef.current = { platforms, handles, enrich_emails }
      setIsBusy(true)
      setError(null)
      setPhase(SCOUT_PHASE.RUNNING)

      try {
        const initialJob = await scoutService.submitJob({ platforms, handles, enrich_emails })
        setJob(initialJob)
        pollJob(initialJob.job_id)
      } catch (err) {
        setError(err.message || "Failed to initialize Scout job")
        setPhase(SCOUT_PHASE.ERROR)
        setIsBusy(false)
      }
    },
    [pollJob]
  )

  const retry = useCallback(() => {
    if (lastParamsRef.current) {
      submit(lastParamsRef.current)
    }
  }, [submit])

  const exportCsv = useCallback(async () => {
    if (!job?.job_id) return
    try {
      await scoutService.exportCsv(job.job_id)
    } catch (err) {
      console.error("Export error:", err)
    }
  }, [job])

  return {
    phase,
    job,
    leads,
    selectedLead,
    setSelectedLead,
    error,
    isBusy,
    submit,
    retry,
    exportCsv,
  }
}
