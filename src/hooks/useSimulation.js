import { useCallback, useState } from "react"
import { simulationService } from "@/services"

export const SIM_PHASE = {
  IDLE: "idle",
  RUNNING: "running",
  READY: "ready",
  ERROR: "error",
}

/**
 * Synthetic-audience simulation is a single request/response call (a few
 * LLM persona role-plays), not a long-running job — no polling needed,
 * unlike media generation.
 */
export function useSimulation() {
  const [phase, setPhase] = useState(SIM_PHASE.IDLE)
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)

  const run = useCallback(async (creativeId, segmentIds) => {
    setPhase(SIM_PHASE.RUNNING)
    setError(null)
    setReport(null)
    try {
      const result = await simulationService.simulate(creativeId, { segment_ids: segmentIds })
      setReport(result)
      setPhase(SIM_PHASE.READY)
      return result
    } catch (err) {
      const msg = err?.message || (typeof err === "string" ? err : "Simulation request failed")
      setError(msg)
      setPhase(SIM_PHASE.ERROR)
      throw err
    }
  }, [])

  const reset = useCallback(() => {
    setPhase(SIM_PHASE.IDLE)
    setReport(null)
    setError(null)
  }, [])

  return {
    phase,
    report,
    error,
    run,
    reset,
    isBusy: phase === SIM_PHASE.RUNNING,
  }
}
