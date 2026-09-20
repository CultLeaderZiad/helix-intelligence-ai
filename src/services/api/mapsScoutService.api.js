import { request } from "../http"
import { API_BASE_URL } from "../config"

export const mapsScoutApi = {
  submitJob(params = {}) {
    return request("/scout/maps/jobs", {
      method: "POST",
      body: {
        keyword: params.keyword || "",
        city: params.city || "",
        depth: Number(params.depth) || 5,
        extract_emails: params.extract_emails !== false,
        pull_socials: Boolean(params.pull_socials),
      },
    })
  },

  getJob(jobId) {
    return request(`/scout/maps/jobs/${jobId}`)
  },

  getLeads(jobId) {
    return request(`/scout/maps/jobs/${jobId}/leads`)
  },

  getOrgJobs() {
    return request("/scout/maps/org-jobs")
  },

  exportCsv(jobId) {
    const token = localStorage.getItem("helix_access_token") || localStorage.getItem("helix_auth_token") || ""
    const exportUrl = `${API_BASE_URL}/scout/maps/export?job_id=${encodeURIComponent(jobId)}`
    
    return fetch(exportUrl, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to export Maps CSV")
        return res.blob()
      })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `helix_maps_leads_${jobId.substring(0, 8)}.csv`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        return { status: "ok" }
      })
  },
}

export default mapsScoutApi
