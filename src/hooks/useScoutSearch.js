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
    async ({ platforms, handles, enrich_emails = true, target_category = "", generate_outreach = true }) => {
      lastParamsRef.current = { platforms, handles, enrich_emails, target_category, generate_outreach }
      setIsBusy(true)
      setError(null)
      setPhase(SCOUT_PHASE.RUNNING)

      try {
        const initialJob = await scoutService.submitJob({
          platforms,
          handles,
          enrich_emails,
          target_category,
          generate_outreach,
        })
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

  const loadJob = useCallback(async (jobId) => {
    if (!jobId) return
    setIsBusy(true)
    setError(null)
    try {
      const [fetchedJob, leadsData] = await Promise.all([
        scoutService.getJob(jobId),
        scoutService.getLeads(jobId),
      ])
      setJob(fetchedJob)
      const items = leadsData.items || []
      setLeads(items)
      setSelectedLead(items[0] || null)
      if (fetchedJob.status === "running" || fetchedJob.status === "queued") {
        setPhase(SCOUT_PHASE.RUNNING)
        setIsBusy(true)
        pollJob(jobId)
      } else if (fetchedJob.status === "failed") {
        setPhase(SCOUT_PHASE.ERROR)
        setError(fetchedJob.error_msg || "Scout job failed")
      } else {
        setPhase(SCOUT_PHASE.READY)
      }
    } catch (err) {
      console.warn("Failed to load scout job:", err)
      setError(err.message || "Failed to load job")
    } finally {
      setIsBusy(false)
    }
  }, [pollJob])

  const loadLatestJob = useCallback(async () => {
    try {
      const res = await scoutService.getLatestJob?.()
      if (res && res.job) {
        setJob(res.job)
        const items = res.leads || []
        setLeads(items)
        setSelectedLead(items[0] || null)
        if (res.job.status === "running" || res.job.status === "queued") {
          setPhase(SCOUT_PHASE.RUNNING)
          setIsBusy(true)
          pollJob(res.job.job_id)
        } else if (res.job.status === "failed") {
          setPhase(SCOUT_PHASE.ERROR)
          setError(res.job.error_msg || "Scout job failed")
        } else {
          setPhase(SCOUT_PHASE.READY)
        }
      }
    } catch (err) {
      // Quietly ignore if no previous runs exist
    }
  }, [pollJob])

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
    loadJob,
    loadLatestJob,
  }
}
