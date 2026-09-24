import { useState, useEffect, useRef, useCallback } from "react"
import { leadgenService } from "@/services"

/**
 * useLeadGenJob - the ONLY caller of leadgenService (Page -> hook -> @/services).
 *
 * State machine:
 *   idle -> validating -> enqueueing -> polling(queued|running|paused) -> succeeded|failed
 *                            \-> worker_offline (honest ErrorState, never fake leads)
 *
 * Long work returns a Job immediately; we poll the real envelope (~1.5s) whose
 * logs/counters come straight from the Scrapling worker. When the worker is
 * down the API answers 503 worker_offline and we surface it as its own phase.
 */
export const LEADGEN_PHASE = {
  IDLE: "idle",
  VALIDATING: "validating",
  ENQUEUEING: "enqueueing",
  POLLING: "polling",
  READY: "succeeded",
  FAILED: "failed",
  WORKER_OFFLINE: "worker_offline",
}

const POLL_MS = 1500
const PAUSED_POLL_MS = 3000

export function useLeadGenJob() {
  const [phase, setPhase] = useState(LEADGEN_PHASE.IDLE)
  const [job, setJob] = useState(null)
  const [leads, setLeads] = useState([])
  const [selectedLead, setSelectedLead] = useState(null)
  const [health, setHealth] = useState(null)
  const [recipes, setRecipes] = useState([])
  const [error, setError] = useState(null)
  const [isBusy, setIsBusy] = useState(false)
  const pollTimerRef = useRef(null)

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  useEffect(() => () => stopPolling(), [stopPolling])

  const fetchLeads = useCallback(async (jobId) => {
    try {
      const data = await leadgenService.getLeads(jobId)
      const items = data.items || []
      setLeads(items)
      setSelectedLead((prev) => items.find((l) => l.id === prev?.id) || items[0] || null)
      return items
    } catch {
      return []
    }
  }, [])

  const pollJob = useCallback(
    (jobId) => {
      stopPolling()
      const tick = async () => {
        try {
          const updated = await leadgenService.getJob(jobId)
          setJob(updated)

          if (updated.status === "succeeded") {
            stopPolling()
            await fetchLeads(jobId)
            setPhase(LEADGEN_PHASE.READY)
            setIsBusy(false)
          } else if (updated.status === "failed") {
            stopPolling()
            setError(updated.error_msg || "Lead Generation job failed")
            await fetchLeads(jobId) // partial leads + honest failure logs stay visible
            setPhase(LEADGEN_PHASE.FAILED)
            setIsBusy(false)
          } else {
            // queued | running | paused - refresh leads so far (real rows only)
            if ((updated.leads_count || 0) > 0) fetchLeads(jobId)
            if (updated.status === "paused" && pollTimerRef.current) {
              clearInterval(pollTimerRef.current)
              pollTimerRef.current = setInterval(tick, PAUSED_POLL_MS)
            }
          }
        } catch (err) {
          stopPolling()
          setError(err.message || "Failed to retrieve job status")
          setPhase(LEADGEN_PHASE.FAILED)
          setIsBusy(false)
        }
      }
      tick()
      pollTimerRef.current = setInterval(tick, POLL_MS)
    },
    [stopPolling, fetchLeads]
  )

  /** Validate client-side (server re-validates), enqueue, start polling. */
  const createJob = useCallback(
    async (payload) => {
      setPhase(LEADGEN_PHASE.VALIDATING)
      setError(null)
      setIsBusy(true)

      const brief = payload?.brief
      const seeds = payload?.seeds
      if (!brief?.icp || brief.icp.trim().length < 3) {
        setError("Brief stage failed: ICP is required (min 3 characters)")
        setPhase(LEADGEN_PHASE.IDLE)
        setIsBusy(false)
        return null
      }
      if ((brief.max_pages || 1) < 1 || (brief.max_leads || 1) < 1) {
        setError("Brief stage failed: max pages and max leads must be at least 1")
        setPhase(LEADGEN_PHASE.IDLE)
        setIsBusy(false)
        return null
      }
      const hasSeeds =
        (seeds?.urls || []).some((u) => u.trim()) || seeds?.sitemap_url || seeds?.shopify_url || seeds?.domains_csv
      if (!hasSeeds) {
        setError("Seed stage failed: provide at least one URL, sitemap, Shopify store, or domain list")
        setPhase(LEADGEN_PHASE.IDLE)
        setIsBusy(false)
        return null
      }

      setPhase(LEADGEN_PHASE.ENQUEUEING)
      try {
        const initial = await leadgenService.createJob(payload)
        setJob(initial)
        setPhase(LEADGEN_PHASE.POLLING)
        pollJob(initial.job_id)
        return initial
      } catch (err) {
        const offline = err?.code === "worker_offline" || err?.status === 503
        setError(
          err?.message ||
            "Lead Generation worker is offline. Start the Scrapling worker and try again."
        )
        setPhase(offline ? LEADGEN_PHASE.WORKER_OFFLINE : LEADGEN_PHASE.FAILED)
        setIsBusy(false)
        return null
      }
    },
    [pollJob]
  )

  const pause = useCallback(async () => {
    if (!job?.job_id) return
    try {
      const updated = await leadgenService.pause(job.job_id)
      setJob(updated)
    } catch (err) {
      setError(err.message || "Pause failed")
    }
  }, [job])

  const resume = useCallback(async () => {
    if (!job?.job_id) return
    try {
      const updated = await leadgenService.resume(job.job_id)
      setJob(updated)
      setPhase(LEADGEN_PHASE.POLLING)
      setIsBusy(true)
      pollJob(job.job_id)
    } catch (err) {
      setError(err.message || "Resume failed")
    }
  }, [job, pollJob])

  const refresh = useCallback(async () => {
    if (!job?.job_id) return
    try {
      const updated = await leadgenService.getJob(job.job_id)
      setJob(updated)
      await fetchLeads(job.job_id)
    } catch (err) {
      setError(err.message || "Refresh failed")
    }
  }, [job, fetchLeads])

  const exportCsv = useCallback(() => {
    if (!job?.job_id) return Promise.resolve()
    return leadgenService.exportCsv(job.job_id)
  }, [job])

  const exportJsonl = useCallback(() => {
    if (!job?.job_id) return Promise.resolve()
    return leadgenService.exportJsonl(job.job_id)
  }, [job])

  const selectLead = useCallback((lead) => setSelectedLead(lead), [])

  const reset = useCallback(() => {
    stopPolling()
    setPhase(LEADGEN_PHASE.IDLE)
    setJob(null)
    setLeads([])
    setSelectedLead(null)
    setError(null)
    setIsBusy(false)
  }, [stopPolling])

  /** Worker/proxy/robots truth - SettingsStrip renders ONLY this. */
  const fetchHealth = useCallback(async () => {
    try {
      const h = await leadgenService.getWorkerHealth()
      setHealth(h)
      return h
    } catch {
      setHealth({ worker: "offline", browsers_ready: false, engines: [], proxy: "off", robots_default: true, queue_depth: 0 })
      return null
    }
  }, [])

  const fetchRecipes = useCallback(async () => {
    try {
      const data = await leadgenService.getRecipes()
      setRecipes(data.items || [])
      return data.items || []
    } catch {
      setRecipes([])
      return []
    }
  }, [])

  return {
    phase, job, leads, selectedLead, health, recipes, error, isBusy,
    createJob, pause, resume, refresh, exportCsv, exportJsonl,
    selectLead, reset, fetchHealth, fetchRecipes,
  }
}

export default useLeadGenJob
