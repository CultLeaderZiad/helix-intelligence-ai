import { request } from "../http"

const monitorService = {
  listMonitors() {
    return request("/monitors/")
  },

  createMonitor(payload) {
    return request("/monitors/", {
      method: "POST",
      body: payload,
    })
  },

  /** W9-2: the pre-filled brand monitor and its record cost (0 records). */
  previewBrandMonitor({ page_id = null, brand_name = null, cadence = "weekly" } = {}) {
    return request("/monitors/brand/preview", { params: { page_id: page_id || null, brand_name: brand_name || null, cadence } })
  },

  /** W9-2 one-click "Monitor this brand". */
  createBrandMonitor({ page_id = null, brand_name = null, cadence = "weekly" } = {}) {
    return request("/monitors/brand", { method: "POST", body: { page_id, brand_name, cadence } })
  },

  updateMonitor(monitorId, changes) {
    return request(`/monitors/${monitorId}`, {
      method: "PATCH",
      body: changes,
    })
  },

  deleteMonitor(monitorId) {
    return request(`/monitors/${monitorId}`, {
      method: "DELETE",
    })
  },

  runNow(monitorId) {
    return request(`/monitors/${monitorId}/run`, {
      method: "POST",
    })
  },

  /** @param {{ monitorId?: string, limit?: number }} [options] */
  listEvents({ monitorId, limit = 50 } = {}) {
    const params = new URLSearchParams()
    if (monitorId) params.set("monitor_id", monitorId)
    params.set("limit", String(limit))
    return request(`/monitors/events?${params.toString()}`)
  },
}

export default monitorService
