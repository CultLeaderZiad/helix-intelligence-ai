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

  listEvents({ monitorId, limit = 50 } = {}) {
    const params = new URLSearchParams()
    if (monitorId) params.set("monitor_id", monitorId)
    params.set("limit", String(limit))
    return request(`/monitors/events?${params.toString()}`)
  },
}

export default monitorService
