import { useState, useEffect, useRef, useCallback } from "react"
import { mapsScoutService } from "@/services"

export const MAPS_SCOUT_PHASE = {
  IDLE: "idle",
  RUNNING: "running",
  READY: "ready",
  ERROR: "error",
}

export function useMapsScoutSearch() {
  const [phase, setPhase] = useState(MAPS_SCOUT_PHASE.IDLE)
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
          const updatedJob = await mapsScoutService.getJob(jobId)
          setJob(updatedJob)

          if (updatedJob.status === "succeeded") {
            stopPolling()
            const leadsData = await mapsScoutService.getLeads(jobId)
            const items = leadsData.items || []
            setLeads(items)
            setSelectedLead(items[0] || null)
            setPhase(MAPS_SCOUT_PHASE.READY)
            setIsBusy(false)
          } else if (updatedJob.status === "failed") {
            stopPolling()
            setError(updatedJob.error_msg || "Maps Scout job encountered an error")
            setPhase(MAPS_SCOUT_PHASE.ERROR)
            setIsBusy(false)
          }
        } catch (err) {
          stopPolling()
          setError(err.message || "Failed to retrieve Maps job status")
          setPhase(MAPS_SCOUT_PHASE.ERROR)
          setIsBusy(false)
        }
      }, 750)
    },
    [stopPolling]
  )

  const submit = useCallback(
    async ({ keyword, city, depth = 5, extract_emails = true, pull_socials = false }) => {
      lastParamsRef.current = { keyword, city, depth, extract_emails, pull_socials }
      setIsBusy(true)
      setError(null)
      setPhase(MAPS_SCOUT_PHASE.RUNNING)

      try {
        const initialJob = await mapsScoutService.submitJob({
          keyword,
          city,
          depth,
          extract_emails,
          pull_socials,
        })
        setJob(initialJob)
        pollJob(initialJob.job_id)
      } catch (err) {
        setError(err.message || "Failed to initialize Maps Scout job")
        setPhase(MAPS_SCOUT_PHASE.ERROR)
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
      await mapsScoutService.exportCsv(job.job_id)
    } catch (err) {
      console.error("Maps Export error:", err)
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
