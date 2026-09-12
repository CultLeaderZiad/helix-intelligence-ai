import { request } from "../http"

/**
 * FastAPI-backed synthetic-audience simulation service.
 *
 * Expected endpoints:
 *   GET  /simulation/segments                        -> PersonaSegment[]
 *   POST /simulation/creatives/{id}/simulate          -> SimulationReport
 */
const simulationService = {
  listSegments() {
    return request("/simulation/segments")
  },

  simulate(creativeId, { segment_ids = [], byok_key = null, byok_provider = null } = {}) {
    return request(`/simulation/creatives/${creativeId}/simulate`, {
      method: "POST",
      body: { segment_ids, byok_key, byok_provider },
    })
  },
}

export default simulationService
