import { request } from "../http"
import { API_BASE_URL } from "../config"

/**
 * Lead Generation service (engine: scrapling_engine).
 * Thin HTTP client for /api/v1/scout/leadgen — the ONLY caller should be
 * useLeadGenJob (Page → hook → @/services architecture rule).
 */
export const leadgenApi = {
  /** Create + enqueue a job. Throws {code:'worker_offline'} when the worker is down. */
  createJob(payload) {
    return request("/scout/leadgen/jobs", { method: "POST", body: payload })
  },

  /** Poll the honest job envelope (status/stage/logs/counters). */
  getJob(jobId) {
    return request(`/scout/leadgen/jobs/${jobId}`)
  },

  getLeads(jobId) {
    return request(`/scout/leadgen/jobs/${jobId}/leads`)
  },

  getLead(jobId, leadId) {
    return request(`/scout/leadgen/jobs/${jobId}/leads/${leadId}`)
  },

  pause(jobId) {
    return request(`/scout/leadgen/jobs/${jobId}/pause`, { method: "POST" })
  },

  resume(jobId) {
    return request(`/scout/leadgen/jobs/${jobId}/resume`, { method: "POST" })
  },

  getRecipes() {
    return request("/scout/leadgen/recipes")
  },

  getWorkerHealth() {
    return request("/scout/leadgen/worker/health")
  },

  _authorizedFetch(url) {
    const token = localStorage.getItem("helix_access_token") || localStorage.getItem("helix_auth_token") || ""
    return fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  },

  /** Download CSV with provenance columns. */
  async exportCsv(jobId) {
    const res = await this._authorizedFetch(`${API_BASE_URL}/scout/leadgen/jobs/${jobId}/export.csv`)
    if (!res.ok) throw new Error("Failed to export CSV")
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `helix_leadgen_${jobId.substring(0, 8)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    return { status: "ok" }
  },

  /** Download JSONL with provenance columns. */
  async exportJsonl(jobId) {
    const res = await this._authorizedFetch(`${API_BASE_URL}/scout/leadgen/jobs/${jobId}/export.jsonl`)
    if (!res.ok) throw new Error("Failed to export JSONL")
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `helix_leadgen_${jobId.substring(0, 8)}.jsonl`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    return { status: "ok" }
  },
}

export default leadgenApi
