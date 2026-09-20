import { request } from "../http"
import { API_BASE_URL } from "../config"

export const scoutApi = {
  submitJob(params = {}) {
    return request("/scout/jobs", {
      method: "POST",
      body: {
        platforms: params.platforms || ["instagram", "github", "linktree"],
        handles: params.handles || [],
        enrich_emails: params.enrich_emails !== false,
      },
    })
  },

  getJob(jobId) {
    return request(`/scout/jobs/${jobId}`)
  },

  getLeads(jobId) {
    return request(`/scout/jobs/${jobId}/leads`)
  },

  getOrgJobs() {
    return request("/scout/org-jobs")
  },

  getLatestJob() {
    return request("/scout/latest-job")
  },

  exportCsv(jobId) {
    const token = localStorage.getItem("helix_access_token") || localStorage.getItem("helix_auth_token") || ""
    const exportUrl = `${API_BASE_URL}/scout/export?job_id=${encodeURIComponent(jobId)}`
    
    // Trigger download with auth header
    return fetch(exportUrl, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to export CSV")
        return res.blob()
      })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `helix_scout_leads_${jobId.substring(0, 8)}.csv`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        return { status: "ok" }
      })
  },

  getSettings() {
    return request("/scout/settings")
  },

  updateSettings(settings) {
    return request("/scout/settings", {
      method: "POST",
      body: settings,
    })
  },
}

export default scoutApi
